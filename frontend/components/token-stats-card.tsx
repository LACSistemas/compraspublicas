"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { EstatsFase } from "@/lib/types";

interface Props {
  titulo: string;
  stats: EstatsFase;
  compact?: boolean;
}

function fmt(n: number, decimais = 0) {
  return n.toLocaleString("pt-BR", { maximumFractionDigits: decimais });
}

const METRICAS = [
  { label: "Chamadas", key: "total_chamadas" as const, decimais: 0 },
  { label: "Média", key: "media" as const, decimais: 1 },
  { label: "Mediana", key: "mediana" as const, decimais: 1 },
  { label: "Mínimo", key: "minimo" as const, decimais: 0 },
  { label: "Máximo", key: "maximo" as const, decimais: 0 },
  { label: "Variância", key: "variancia" as const, decimais: 1 },
];

export function TokenStatsCard({ titulo, stats, compact = false }: Props) {
  if (stats.total_chamadas === 0) {
    return null;
  }

  return (
    <Card className={compact ? "text-xs" : ""}>
      <CardHeader className={compact ? "pb-2 pt-3 px-4" : undefined}>
        <CardTitle className={compact ? "text-sm font-semibold" : "text-base"}>
          {titulo}
        </CardTitle>
      </CardHeader>
      <CardContent className={compact ? "px-4 pb-3" : undefined}>
        <div className="grid grid-cols-3 gap-x-4 gap-y-2">
          {METRICAS.map(({ label, key, decimais }) => (
            <div key={key}>
              <p className="text-muted-foreground" style={{ fontSize: compact ? "10px" : "11px" }}>
                {label}
              </p>
              <p className={`font-semibold tabular-nums ${compact ? "text-xs" : "text-sm"}`}>
                {fmt(stats[key], decimais)}
              </p>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
