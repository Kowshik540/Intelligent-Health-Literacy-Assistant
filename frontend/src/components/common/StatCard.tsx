type StatCardProps = {
  label: string;
  value: string;
  detail: string;
};

export default function StatCard({
  label,
  value,
  detail,
}: StatCardProps) {
  return (
    <div className="stat-card">
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      <div className="stat-detail">{detail}</div>
    </div>
  );
}