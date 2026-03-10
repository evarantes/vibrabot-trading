from datetime import date

from codexiaauditor.invoice_parser import (
    parse_access_key_metadata,
    parse_emission_date_to_date,
    parse_nfe_xml,
)


def test_parse_access_key_metadata():
    data = parse_access_key_metadata("35240212345678000190550010000001231000001234")
    assert data["invoice_number"] == "123"
    assert data["series"] == "1"
    assert data["cnpj_issuer"] == "12345678000190"


def test_parse_nfe_xml_extracts_items():
    sample_xml = """
    <nfeProc xmlns="http://www.portalfiscal.inf.br/nfe">
      <NFe>
        <infNFe Id="NFe35240212345678000190550010000001231000001234">
          <ide>
            <nNF>123</nNF>
            <serie>1</serie>
            <dEmi>2026-03-10</dEmi>
          </ide>
          <emit>
            <xNome>Fornecedor Teste</xNome>
          </emit>
          <det nItem="1">
            <prod>
              <xProd>TOALHA DE MESA</xProd>
              <qCom>100.0000</qCom>
              <vUnCom>30.00</vUnCom>
              <vProd>3000.00</vProd>
            </prod>
          </det>
        </infNFe>
      </NFe>
    </nfeProc>
    """.strip().encode("utf-8")

    parsed = parse_nfe_xml(sample_xml)
    assert parsed["invoice_number"] == "123"
    assert parsed["series"] == "1"
    assert parsed["emission_date"] == "2026-03-10"
    assert len(parsed["items"]) == 1
    assert parsed["items"][0]["description"] == "TOALHA DE MESA"
    assert parsed["items"][0]["quantity"] == 100.0


def test_parse_emission_date_to_date():
    assert parse_emission_date_to_date("2026-03-10") == date(2026, 3, 10)
    assert parse_emission_date_to_date("10/03/2026") == date(2026, 3, 10)
