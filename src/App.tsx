import { FormEvent, useEffect, useMemo, useState } from "react";
import { generateAuditSummary } from "./analysis";
import { loadItems, loadMovements, persistState, resetDemoState } from "./storage";
import { DailyMovement, LinenItem, MovementType, Severity } from "./types";

const currencyFormatter = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
  maximumFractionDigits: 0
});

const numberFormatter = new Intl.NumberFormat("pt-BR");

const percentFormatter = new Intl.NumberFormat("pt-BR", {
  style: "percent",
  maximumFractionDigits: 0
});

const movementLabels: Record<MovementType, string> = {
  purchase: "Compra / reposicao",
  laundry_out: "Envio para lavanderia",
  laundry_in: "Retorno da lavanderia",
  allocated_use: "Liberado para uso",
  returned_use: "Retorno do uso",
  loss: "Perda / avaria"
};

const severityLabels: Record<Severity, string> = {
  critico: "Critico",
  alto: "Alto",
  moderado: "Moderado",
  estavel: "Estavel"
};

interface FeedbackState {
  kind: "success" | "error";
  message: string;
}

interface MovementFormState {
  data: string;
  itemId: string;
  tipo: MovementType;
  quantidade: number;
  setor: string;
  responsavel: string;
  observacao: string;
}

function getCurrentDateTime(): string {
  const now = new Date();
  const timezoneOffset = now.getTimezoneOffset() * 60000;
  return new Date(now.getTime() - timezoneOffset).toISOString().slice(0, 16);
}

function normalizeDate(value: string): string {
  return value.replace("T", " ");
}

function buildInitialForm(items: LinenItem[]): MovementFormState {
  return {
    data: getCurrentDateTime(),
    itemId: items[0]?.id ?? "",
    tipo: "laundry_out",
    quantidade: 1,
    setor: "Lavanderia",
    responsavel: "",
    observacao: ""
  };
}

function moveToLoss(item: LinenItem, quantidade: number): LinenItem {
  let remaining = quantidade;
  let estoqueAtual = item.estoqueAtual;
  let emUso = item.emUso;
  let emLavanderia = item.emLavanderia;

  const reduce = (value: number): [number, number] => {
    const consumed = Math.min(value, remaining);
    remaining -= consumed;
    return [value - consumed, remaining];
  };

  [estoqueAtual] = reduce(estoqueAtual);
  [emUso] = reduce(emUso);
  [emLavanderia] = reduce(emLavanderia);

  return {
    ...item,
    estoqueAtual,
    emUso,
    emLavanderia,
    perdasRegistradas: item.perdasRegistradas + quantidade
  };
}

function applyMovement(item: LinenItem, tipo: MovementType, quantidade: number, data: string): { nextItem?: LinenItem; error?: string } {
  if (quantidade <= 0) {
    return { error: "A quantidade deve ser maior que zero." };
  }

  let nextItem: LinenItem = { ...item };

  switch (tipo) {
    case "purchase":
      nextItem.compradoTotal += quantidade;
      nextItem.estoqueAtual += quantidade;
      break;
    case "laundry_out":
      if (quantidade > item.estoqueAtual) {
        return { error: "Nao ha estoque suficiente para enviar essa quantidade para lavanderia." };
      }
      nextItem.estoqueAtual -= quantidade;
      nextItem.emLavanderia += quantidade;
      nextItem.lavanderiaEnviadoHoje += quantidade;
      break;
    case "laundry_in":
      if (quantidade > item.emLavanderia) {
        return { error: "Nao ha essa quantidade registrada em lavanderia para retornar." };
      }
      nextItem.emLavanderia -= quantidade;
      nextItem.estoqueAtual += quantidade;
      nextItem.lavanderiaRetornadoHoje += quantidade;
      break;
    case "allocated_use":
      if (quantidade > item.estoqueAtual) {
        return { error: "Nao ha estoque suficiente para liberar essa quantidade para uso." };
      }
      nextItem.estoqueAtual -= quantidade;
      nextItem.emUso += quantidade;
      nextItem.usoMovimentadoHoje += quantidade;
      break;
    case "returned_use":
      if (quantidade > item.emUso) {
        return { error: "Nao ha essa quantidade registrada em uso para retornar." };
      }
      nextItem.emUso -= quantidade;
      nextItem.estoqueAtual += quantidade;
      nextItem.usoMovimentadoHoje += quantidade;
      break;
    case "loss":
      if (quantidade > item.estoqueAtual + item.emUso + item.emLavanderia) {
        return { error: "A perda informada excede o total atualmente rastreado para esse item." };
      }
      nextItem = moveToLoss(item, quantidade);
      break;
    default:
      return { error: "Tipo de movimento invalido." };
  }

  nextItem.ultimaContagem = normalizeDate(data);
  return { nextItem };
}

function SeverityBadge({ severity }: { severity: Severity }) {
  return <span className={`severity-badge severity-${severity}`}>{severityLabels[severity]}</span>;
}

function KpiCard({ label, value, caption }: { label: string; value: string; caption: string }) {
  return (
    <article className="panel kpi-card">
      <span className="kpi-label">{label}</span>
      <div className="kpi-value">{value}</div>
      <div className="kpi-caption">{caption}</div>
    </article>
  );
}

export default function App() {
  const [items, setItems] = useState<LinenItem[]>(() => loadItems());
  const [movements, setMovements] = useState<DailyMovement[]>(() => loadMovements());
  const [form, setForm] = useState<MovementFormState>(() => buildInitialForm(loadItems()));
  const [feedback, setFeedback] = useState<FeedbackState | null>(null);

  useEffect(() => {
    persistState(items, movements);
  }, [items, movements]);

  useEffect(() => {
    if (!items.find((item) => item.id === form.itemId)) {
      setForm((current) => ({
        ...current,
        itemId: items[0]?.id ?? ""
      }));
    }
  }, [items, form.itemId]);

  const summary = useMemo(() => generateAuditSummary(items), [items]);

  const currentItem = useMemo(
    () => items.find((item) => item.id === form.itemId) ?? null,
    [items, form.itemId]
  );

  const recentMovements = useMemo(
    () => [...movements].sort((left, right) => right.data.localeCompare(left.data)).slice(0, 8),
    [movements]
  );

  const recommendedChecks = useMemo(() => {
    const checks = summary.itensCriticos.slice(0, 3).map((audit) => ({
      title: `Recontar ${audit.itemNome}`,
      text: `${audit.desaparecidas} pecas sem conciliacao. Foco: ${audit.focoProvavel.toLowerCase()}.`
    }));

    if (summary.riscosPorSetor[0]) {
      checks.unshift({
        title: `Auditar ${summary.riscosPorSetor[0].setor}`,
        text: `Area com maior risco consolidado e ${currencyFormatter.format(summary.riscosPorSetor[0].valorEmRisco)} potencialmente expostos.`
      });
    }

    if (checks.length === 0) {
      checks.push({
        title: "Manter disciplina operacional",
        text: "Continue registrando compras, saidas para lavanderia e devolucoes para preservar a rastreabilidade."
      });
    }

    return checks.slice(0, 4);
  }, [summary.itensCriticos, summary.riscosPorSetor]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFeedback(null);

    if (!form.itemId) {
      setFeedback({ kind: "error", message: "Selecione um item de enxoval para registrar o movimento." });
      return;
    }

    if (!form.responsavel.trim()) {
      setFeedback({ kind: "error", message: "Informe o responsavel pelo movimento." });
      return;
    }

    const item = items.find((current) => current.id === form.itemId);

    if (!item) {
      setFeedback({ kind: "error", message: "O item selecionado nao foi encontrado." });
      return;
    }

    const { nextItem, error } = applyMovement(item, form.tipo, form.quantidade, form.data);

    if (error || !nextItem) {
      setFeedback({ kind: "error", message: error ?? "Nao foi possivel registrar o movimento." });
      return;
    }

    const movement: DailyMovement = {
      id: `mov-${Date.now()}`,
      data: normalizeDate(form.data),
      itemId: form.itemId,
      tipo: form.tipo,
      quantidade: form.quantidade,
      setor: form.setor.trim() || "Operacao",
      responsavel: form.responsavel.trim(),
      observacao: form.observacao.trim()
    };

    setItems((current) => current.map((listedItem) => (listedItem.id === item.id ? nextItem : listedItem)));
    setMovements((current) => [movement, ...current]);
    setFeedback({ kind: "success", message: "Movimento registrado e auditoria recalculada com sucesso." });
    setForm((current) => ({
      ...current,
      data: getCurrentDateTime(),
      quantidade: 1,
      responsavel: "",
      observacao: ""
    }));
  };

  const handleReset = () => {
    const demo = resetDemoState();
    setItems(demo.items);
    setMovements(demo.movements);
    setForm(buildInitialForm(demo.items));
    setFeedback({ kind: "success", message: "Base demo restaurada para o estado inicial do CODEXIAAUDITOR." });
  };

  return (
    <main className="app-shell">
      <section className="hero">
        <div className="panel hero-main">
          <span className="eyebrow">CODEXIAAUDITOR</span>
          <h1>Auditoria inteligente do enxoval hoteleiro</h1>
          <p>
            Controle compras, estoque, lavanderia, uso diario e perdas em um unico painel. O motor de
            analise cruza o que foi comprado com o que esta fisicamente rastreado para mostrar onde o
            desfalque pode estar acontecendo.
          </p>
          <div className="hero-highlights">
            <div className="pill">Comprado x estoque conciliado</div>
            <div className="pill">Rastreio diario da lavanderia</div>
            <div className="pill">Uso por governanca e andares</div>
            <div className="pill">IA operacional para desvios</div>
          </div>
        </div>

        <aside className="panel hero-side">
          <div>
            <h2>IA auditora em tempo real</h2>
            <p>
              A analise identifica lacunas entre o total comprado e o total rastreado, priorizando o
              setor que mais concentra risco neste momento.
            </p>
          </div>
          <div>
            <span className="kpi-label">Valor potencial em risco</span>
            <div className="risk-value">{currencyFormatter.format(summary.valorEmRisco)}</div>
            <p>{summary.relatorioExecutivo}</p>
          </div>
        </aside>
      </section>

      <section className="grid-kpis">
        <KpiCard
          label="Enxoval comprado"
          value={numberFormatter.format(summary.totalComprado)}
          caption="Base total adquirida pelo hotel."
        />
        <KpiCard
          label="Estoque atual"
          value={numberFormatter.format(summary.totalEstoque)}
          caption="Pecas fisicamente disponiveis agora."
        />
        <KpiCard
          label="Em lavanderia"
          value={numberFormatter.format(summary.totalEmLavanderia)}
          caption="Lotes fora do estoque aguardando retorno."
        />
        <KpiCard
          label="Em uso"
          value={numberFormatter.format(summary.totalEmUso)}
          caption="Pecas atualmente alocadas na operacao."
        />
        <KpiCard
          label="Nao conciliadas"
          value={numberFormatter.format(summary.totalDesaparecido)}
          caption={`Perdas declaradas: ${numberFormatter.format(summary.totalPerdas)} pecas.`}
        />
      </section>

      <section className="two-columns">
        <div className="panel section-card">
          <div className="section-title">
            <div>
              <h2>Mapa completo do enxoval</h2>
              <p>Visualize onde cada item esta e quais pecas merecem investigacao imediata.</p>
            </div>
          </div>

          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Item</th>
                  <th>Comprado</th>
                  <th>Estoque / minimo</th>
                  <th>Lavanderia</th>
                  <th>Em uso</th>
                  <th>Perdas</th>
                  <th>Nao conciliadas</th>
                  <th>Foco da IA</th>
                  <th>Severidade</th>
                </tr>
              </thead>
              <tbody>
                {summary.auditoriaPorItem.map((audit) => {
                  const item = items.find((current) => current.id === audit.itemId);

                  if (!item) {
                    return null;
                  }

                  return (
                    <tr key={item.id}>
                      <td>
                        <strong>{item.nome}</strong>
                        <span className="table-note">
                          {item.categoria} · ultima contagem {item.ultimaContagem}
                        </span>
                      </td>
                      <td>{numberFormatter.format(item.compradoTotal)}</td>
                      <td>
                        {numberFormatter.format(item.estoqueAtual)} / {numberFormatter.format(item.minimoEstoque)}
                      </td>
                      <td>
                        {numberFormatter.format(item.emLavanderia)}
                        <div className="table-note">
                          retorno hoje {percentFormatter.format(audit.retornoLavanderia)}
                        </div>
                      </td>
                      <td>{numberFormatter.format(item.emUso)}</td>
                      <td>{numberFormatter.format(item.perdasRegistradas)}</td>
                      <td>
                        <strong>{numberFormatter.format(audit.desaparecidas)}</strong>
                        <span className="table-note">{currencyFormatter.format(audit.valorEmRisco)}</span>
                      </td>
                      <td>
                        <strong>{audit.focoProvavel}</strong>
                        <span className="table-note">{audit.mensagem}</span>
                      </td>
                      <td>
                        <SeverityBadge severity={audit.severidade} />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        <aside className="panel analysis-card">
          <div className="subpanel">
            <div className="section-title">
              <div>
                <h2>Leitura executiva da auditoria</h2>
                <p>Resumo orientado para a tomada de decisao da gerencia.</p>
              </div>
            </div>
            <div className="insight-item">
              <strong>Diagnostico da IA</strong>
              <p>{summary.relatorioExecutivo}</p>
            </div>
            <div className="insight-list">
              {summary.insights.map((insight) => (
                <div key={insight.titulo} className="insight-item">
                  <SeverityBadge severity={insight.severidade} />
                  <p>
                    <strong>{insight.titulo}</strong>
                  </p>
                  <p>{insight.descricao}</p>
                </div>
              ))}
            </div>
          </div>
        </aside>
      </section>

      <section className="operations-grid panel">
        <div className="form-card">
          <h3>Lancar movimento diario</h3>
          <p>
            Registre compras, envios para lavanderia, retornos, liberacao para uso e perdas. Cada
            movimento recalcula a auditoria instantaneamente.
          </p>

          <form onSubmit={handleSubmit}>
            <div className="form-grid">
              <label>
                Data e hora
                <input
                  type="datetime-local"
                  value={form.data}
                  onChange={(event) => setForm((current) => ({ ...current, data: event.target.value }))}
                />
              </label>

              <label>
                Item do enxoval
                <select
                  value={form.itemId}
                  onChange={(event) => setForm((current) => ({ ...current, itemId: event.target.value }))}
                >
                  {items.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.nome}
                    </option>
                  ))}
                </select>
              </label>

              <div className="form-grid two">
                <label>
                  Tipo de movimento
                  <select
                    value={form.tipo}
                    onChange={(event) =>
                      setForm((current) => ({ ...current, tipo: event.target.value as MovementType }))
                    }
                  >
                    {Object.entries(movementLabels).map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                </label>

                <label>
                  Quantidade
                  <input
                    type="number"
                    min={1}
                    value={form.quantidade}
                    onChange={(event) =>
                      setForm((current) => ({
                        ...current,
                        quantidade: Math.max(1, Number(event.target.value) || 1)
                      }))
                    }
                  />
                </label>
              </div>

              <div className="form-grid two">
                <label>
                  Setor
                  <input
                    type="text"
                    value={form.setor}
                    onChange={(event) => setForm((current) => ({ ...current, setor: event.target.value }))}
                    placeholder="Lavanderia, governanca, compras..."
                  />
                </label>

                <label>
                  Responsavel
                  <input
                    type="text"
                    value={form.responsavel}
                    onChange={(event) =>
                      setForm((current) => ({ ...current, responsavel: event.target.value }))
                    }
                    placeholder="Nome da pessoa ou equipe"
                  />
                </label>
              </div>

              <label>
                Observacao
                <textarea
                  rows={3}
                  value={form.observacao}
                  onChange={(event) => setForm((current) => ({ ...current, observacao: event.target.value }))}
                  placeholder="Romaneio, justificativa, avaria, conferencia, lote..."
                />
              </label>
            </div>

            {currentItem ? (
              <div className="feedback success">
                Estoque atual: {numberFormatter.format(currentItem.estoqueAtual)} · Em lavanderia:{" "}
                {numberFormatter.format(currentItem.emLavanderia)} · Em uso:{" "}
                {numberFormatter.format(currentItem.emUso)} · Nao conciliadas:{" "}
                {numberFormatter.format(
                  summary.auditoriaPorItem.find((audit) => audit.itemId === currentItem.id)?.desaparecidas ?? 0
                )}
              </div>
            ) : null}

            {feedback ? <div className={`feedback ${feedback.kind}`}>{feedback.message}</div> : null}

            <div className="button-row">
              <button type="submit" className="primary-button">
                Registrar movimento
              </button>
              <button type="button" className="secondary-button" onClick={handleReset}>
                Restaurar base demo
              </button>
            </div>
          </form>
        </div>

        <div className="timeline-card">
          <div className="timeline-header">
            <div>
              <h3>Timeline operacional</h3>
              <p>Ultimos registros que alimentam a auditoria do dia.</p>
            </div>
            <div className="meta-chip">{numberFormatter.format(movements.length)} movimentos</div>
          </div>

          <div className="timeline-list">
            {recentMovements.map((movement) => {
              const item = items.find((current) => current.id === movement.itemId);

              return (
                <div key={movement.id} className="timeline-item">
                  <strong>{movementLabels[movement.tipo]}</strong>
                  <p>
                    {item?.nome ?? movement.itemId} · {numberFormatter.format(movement.quantidade)} pecas
                  </p>
                  <div className="timeline-meta">
                    <span className="meta-chip">{movement.data}</span>
                    <span className="meta-chip">{movement.setor}</span>
                    <span className="meta-chip">{movement.responsavel}</span>
                  </div>
                  {movement.observacao ? <p>{movement.observacao}</p> : null}
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <section className="two-columns">
        <div className="panel section-card">
          <div className="section-title">
            <div>
              <h2>Setores com maior risco</h2>
              <p>Prioridade de investigacao definida automaticamente pela auditoria.</p>
            </div>
          </div>

          {summary.riscosPorSetor.length > 0 ? (
            <div className="risk-list">
              {summary.riscosPorSetor.map((risk) => (
                <div key={risk.setor} className="risk-item">
                  <strong>{risk.setor}</strong>
                  <p>
                    {numberFormatter.format(risk.quantidadeEmRisco)} pecas sob suspeita em{" "}
                    {numberFormatter.format(risk.itensAfetados)} item(ns), equivalente a{" "}
                    {currencyFormatter.format(risk.valorEmRisco)}.
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <p className="empty-state">Sem risco setorial relevante no momento.</p>
          )}
        </div>

        <aside className="panel analysis-card">
          <div className="section-title">
            <div>
              <h2>Proximos passos recomendados</h2>
              <p>Checklist pratico para encontrar o erro operacional.</p>
            </div>
          </div>

          <div className="check-list">
            {recommendedChecks.map((check) => (
              <div key={check.title} className="check-item">
                <strong>{check.title}</strong>
                <p>{check.text}</p>
              </div>
            ))}
          </div>
        </aside>
      </section>

      <p className="footer-note">
        CODEXIAAUDITOR foi estruturado para ser a base de um sistema evolutivo: hoje com inteligencia
        operacional local e pronto para futura integracao com modelos de IA, OCR de romaneios, RFID e
        dashboards gerenciais.
      </p>
    </main>
  );
}
