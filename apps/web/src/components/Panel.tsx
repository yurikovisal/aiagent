export function Panel({ title, subtitle, children, actions }: {
  title?: string; subtitle?: string; children: React.ReactNode; actions?: React.ReactNode;
}) {
  return (
    <div className="rounded border border-base-border bg-base-panel">
      {(title || actions) && (
        <div className="flex items-center justify-between border-b border-base-border px-4 py-2.5">
          <div>
            {title && <h2 className="text-sm font-medium">{title}</h2>}
            {subtitle && <p className="text-xs text-base-muted">{subtitle}</p>}
          </div>
          {actions}
        </div>
      )}
      <div className="p-4">{children}</div>
    </div>
  );
}

export function EmptyState({ text }: { text: string }) {
  return <p className="py-6 text-center text-xs text-base-muted">{text}</p>;
}
