import { PrismaClient } from "../src/generated/prisma/client";
import { PrismaBetterSqlite3 } from "@prisma/adapter-better-sqlite3";

const adapter = new PrismaBetterSqlite3({ url: "file:dev.db" });
const prisma = new PrismaClient({ adapter });

async function main() {
  console.log("Populando banco de dados com dados de exemplo...\n");

  const toalhas = await prisma.category.create({
    data: { name: "Toalhas", description: "Toalhas de banho, rosto e piso" },
  });

  const lencois = await prisma.category.create({
    data: { name: "Lençóis", description: "Lençóis de cama solteiro e casal" },
  });

  const fronhas = await prisma.category.create({
    data: { name: "Fronhas", description: "Fronhas para travesseiros" },
  });

  const edredons = await prisma.category.create({
    data: { name: "Edredons", description: "Edredons e cobertores" },
  });

  const roupoes = await prisma.category.create({
    data: { name: "Roupões", description: "Roupões de banho" },
  });

  const items = await Promise.all([
    prisma.item.create({
      data: { categoryId: toalhas.id, name: "Toalha de Banho Branca", unit: "unidade", minStock: 100 },
    }),
    prisma.item.create({
      data: { categoryId: toalhas.id, name: "Toalha de Rosto Branca", unit: "unidade", minStock: 100 },
    }),
    prisma.item.create({
      data: { categoryId: toalhas.id, name: "Toalha de Piso", unit: "unidade", minStock: 80 },
    }),
    prisma.item.create({
      data: { categoryId: lencois.id, name: "Lençol Casal Branco", unit: "unidade", minStock: 60 },
    }),
    prisma.item.create({
      data: { categoryId: lencois.id, name: "Lençol Solteiro Branco", unit: "unidade", minStock: 40 },
    }),
    prisma.item.create({
      data: { categoryId: fronhas.id, name: "Fronha Branca 50x70", unit: "unidade", minStock: 120 },
    }),
    prisma.item.create({
      data: { categoryId: edredons.id, name: "Edredom Casal Branco", unit: "unidade", minStock: 30 },
    }),
    prisma.item.create({
      data: { categoryId: roupoes.id, name: "Roupão Adulto Branco", unit: "unidade", minStock: 20 },
    }),
  ]);

  const [toalhaBanho, toalhaRosto, toalhaPiso, lencolCasal, lencolSolteiro, fronha, edredom, roupao] = items;

  const purchaseData = [
    { item: toalhaBanho, qty: 200, price: 25.0, supplier: "Têxtil São Paulo", date: "2025-01-15" },
    { item: toalhaBanho, qty: 100, price: 27.5, supplier: "Têxtil São Paulo", date: "2025-06-20" },
    { item: toalhaRosto, qty: 200, price: 12.0, supplier: "Têxtil São Paulo", date: "2025-01-15" },
    { item: toalhaPiso, qty: 150, price: 18.0, supplier: "Têxtil São Paulo", date: "2025-01-15" },
    { item: lencolCasal, qty: 120, price: 45.0, supplier: "Rede Conforto Ltda", date: "2025-02-10" },
    { item: lencolSolteiro, qty: 80, price: 35.0, supplier: "Rede Conforto Ltda", date: "2025-02-10" },
    { item: fronha, qty: 250, price: 8.0, supplier: "Rede Conforto Ltda", date: "2025-02-10" },
    { item: edredom, qty: 60, price: 120.0, supplier: "Macio Indústria Têxtil", date: "2025-03-05" },
    { item: roupao, qty: 40, price: 85.0, supplier: "Macio Indústria Têxtil", date: "2025-03-05" },
  ];

  for (const p of purchaseData) {
    await prisma.purchase.create({
      data: {
        itemId: p.item.id,
        quantity: p.qty,
        unitPrice: p.price,
        totalPrice: p.qty * p.price,
        supplier: p.supplier,
        invoiceNumber: `NF-${Math.floor(Math.random() * 90000) + 10000}`,
        purchaseDate: new Date(p.date + "T12:00:00.000Z"),
      },
    });
  }

  console.log("  Compras registradas");

  const today = new Date();
  const todayStr = today.toISOString().split("T")[0];

  const stockData = [
    { item: toalhaBanho, qty: 85 },
    { item: toalhaRosto, qty: 72 },
    { item: toalhaPiso, qty: 45 },
    { item: lencolCasal, qty: 35 },
    { item: lencolSolteiro, qty: 28 },
    { item: fronha, qty: 68 },
    { item: edredom, qty: 22 },
    { item: roupao, qty: 12 },
  ];

  for (const s of stockData) {
    await prisma.stockCount.create({
      data: {
        itemId: s.item.id,
        date: new Date(todayStr + "T12:00:00.000Z"),
        quantity: s.qty,
        location: "Almoxarifado Principal",
      },
    });
  }

  console.log("  Estoque registrado");

  for (let d = 6; d >= 0; d--) {
    const date = new Date(today);
    date.setDate(date.getDate() - d);
    const dateStr = date.toISOString().split("T")[0];

    const laundryData = [
      { item: toalhaBanho, sent: 40 + Math.floor(Math.random() * 15), returned: 35 + Math.floor(Math.random() * 10), damaged: Math.floor(Math.random() * 3) },
      { item: toalhaRosto, sent: 35 + Math.floor(Math.random() * 10), returned: 30 + Math.floor(Math.random() * 8), damaged: Math.floor(Math.random() * 2) },
      { item: toalhaPiso, sent: 25 + Math.floor(Math.random() * 10), returned: 22 + Math.floor(Math.random() * 7), damaged: Math.floor(Math.random() * 2) },
      { item: lencolCasal, sent: 20 + Math.floor(Math.random() * 8), returned: 17 + Math.floor(Math.random() * 6), damaged: Math.floor(Math.random() * 2) },
      { item: lencolSolteiro, sent: 12 + Math.floor(Math.random() * 6), returned: 10 + Math.floor(Math.random() * 5), damaged: Math.floor(Math.random() * 1) },
      { item: fronha, sent: 40 + Math.floor(Math.random() * 15), returned: 36 + Math.floor(Math.random() * 10), damaged: Math.floor(Math.random() * 3) },
    ];

    for (const l of laundryData) {
      await prisma.laundryRecord.create({
        data: {
          itemId: l.item.id,
          date: new Date(dateStr + "T12:00:00.000Z"),
          sentQuantity: l.sent,
          returnedQuantity: l.returned,
          damagedQuantity: l.damaged,
        },
      });
    }
  }

  console.log("  Registros de lavanderia criados (7 dias)");

  const rooms = ["101", "102", "103", "104", "105", "201", "202", "203", "204", "205", "301", "302", "303", "304"];

  for (const room of rooms) {
    const roomItems = [
      { item: toalhaBanho, qty: 2 },
      { item: toalhaRosto, qty: 2 },
      { item: toalhaPiso, qty: 1 },
      { item: lencolCasal, qty: 1 },
      { item: fronha, qty: 2 },
    ];

    for (const ri of roomItems) {
      await prisma.roomUsage.create({
        data: {
          itemId: ri.item.id,
          date: new Date(todayStr + "T12:00:00.000Z"),
          roomNumber: room,
          quantity: ri.qty,
        },
      });
    }
  }

  console.log("  Uso nos quartos registrado (14 quartos)");

  console.log("\nDados de exemplo criados com sucesso!");
  console.log("\nResumo:");
  console.log(`  - ${items.length} itens em 5 categorias`);
  console.log(`  - ${purchaseData.length} registros de compra`);
  console.log(`  - Contagem de estoque atualizada`);
  console.log(`  - 7 dias de registros de lavanderia`);
  console.log(`  - ${rooms.length} quartos com enxoval em uso`);
}

main()
  .catch(console.error)
  .finally(() => process.exit(0));
