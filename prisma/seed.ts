import { PrismaClient } from "@prisma/client";

const prisma = new PrismaClient();

async function main() {
  const tipos = [
    { id: "lencol-solteiro", nome: "Lençol Solteiro", descricao: "Lençol de solteiro", parLevel: 50 },
    { id: "lencol-casal", nome: "Lençol Casal", descricao: "Lençol de casal", parLevel: 50 },
    { id: "toalha-banho", nome: "Toalha de Banho", descricao: "Toalha grande para banho", parLevel: 100 },
    { id: "toalha-rosto", nome: "Toalha de Rosto", descricao: "Toalha de rosto", parLevel: 100 },
    { id: "fronha", nome: "Fronha", descricao: "Fronha de travesseiro", parLevel: 100 },
  ];

  for (const tipo of tipos) {
    await prisma.tipoEnxoval.upsert({
      where: { id: tipo.id },
      update: {},
      create: tipo,
    });
  }

  console.log("Tipos de enxoval criados:", tipos.length);
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
