const COLORS: Record<string, string> = {
  CRITICAL: "bg-sev-critical/15 text-sev-critical border-sev-critical/30",
  HIGH: "bg-sev-high/15 text-sev-high border-sev-high/30",
  MEDIUM: "bg-sev-medium/15 text-sev-medium border-sev-medium/30",
  LOW: "bg-sev-low/15 text-sev-low border-sev-low/30",
  INFO: "bg-sev-info/15 text-sev-info border-sev-info/30",
};

const LABELS_RU: Record<string, string> = {
  CRITICAL: "Критично",
  HIGH: "Высокий",
  MEDIUM: "Средний",
  LOW: "Низкий",
  INFO: "Инфо",
};

export function SeverityBadge({ severity }: { severity: string }) {
  const cls = COLORS[severity] || COLORS.INFO;
  return (
    <span className={`inline-flex items-center rounded border px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide ${cls}`}>
      {LABELS_RU[severity] || severity}
    </span>
  );
}
