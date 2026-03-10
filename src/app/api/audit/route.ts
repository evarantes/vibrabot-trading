import { prisma } from "@/lib/prisma";
import { runAudit } from "@/lib/audit-engine";
import { NextResponse } from "next/server";

export async function GET() {
  const reports = await prisma.auditReport.findMany({
    orderBy: { date: "desc" },
  });
  return NextResponse.json(reports);
}

export async function POST() {
  const audit = await runAudit();

  const report = await prisma.auditReport.create({
    data: {
      date: audit.date,
      totalPurchased: audit.totalPurchased,
      totalStock: audit.totalStock,
      totalInLaundry: audit.totalInLaundry,
      totalInUse: audit.totalInUse,
      totalMissing: audit.totalMissing,
      percentMissing: audit.percentMissing,
      findings: JSON.stringify(audit.findings),
      recommendations: JSON.stringify(audit.recommendations),
      riskLevel: audit.riskLevel,
      status: "concluido",
    },
  });

  return NextResponse.json({ report, details: audit }, { status: 201 });
}
