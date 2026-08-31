type FloatingMarkerProps = {
  label: string;
  value: string;
  variant: "evidence" | "safety";
};

export default function FloatingMarker({
  label,
  value,
  variant,
}: FloatingMarkerProps) {
  return (
    <div className={`floating-marker marker-${variant}`}>
      <span className="marker-dot" />
      <span className="marker-label">{label}</span>
      <strong>{value}</strong>
    </div>
  );
}