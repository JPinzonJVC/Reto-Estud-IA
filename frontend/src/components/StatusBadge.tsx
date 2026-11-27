interface StatusBadgeProps {
  status: string;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const normalized = status.toLowerCase();
  const label = status.replaceAll('_', ' ');

  return <span className={`status-badge status-badge--${normalized}`}>{label}</span>;
}
