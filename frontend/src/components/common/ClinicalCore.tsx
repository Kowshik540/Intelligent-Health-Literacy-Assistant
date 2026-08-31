import { MODULES } from "../../data/mockData";

export default function ClinicalCore() {
  return (
    <>
      <div className="panel-heading">
        <div>
          <span className="tiny-label">SYSTEM</span>
          <h2>Clinical Core</h2>
        </div>

        <span className="online-dot" />
      </div>

      <div className="system-visual">
        <div className="mini-orbit">
          <div className="orbit-ring" />
          <div className="orbit-ring orbit-ring-alt" />
          <div className="orbit-core">✦</div>
        </div>

        <div>
          <strong>AI READY</strong>
          <small>
            Verification pipeline operational
          </small>
        </div>
      </div>

      <div className="module-list">
        {MODULES.map((module) => (
          <div
            key={module.title}
            className={
              module.title === "Evidence Retrieval"
                ? "module active-module"
                : "module"
            }
          >
            <div className="module-icon">
              {module.icon}
            </div>

            <div>
              <strong>{module.title}</strong>
              <small>{module.detail}</small>
            </div>

            <span>✓</span>
          </div>
        ))}
      </div>
    </>
  );
}