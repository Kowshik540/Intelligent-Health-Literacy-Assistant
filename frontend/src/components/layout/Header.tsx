import type { Page } from "../../types";

type HeaderProps = {
  activeTab: Page;
  onTabChange: (tab: Page) => void;
};

export default function Header({
  activeTab,
  onTabChange,
}: HeaderProps) {
  const tabs: Page[] = [
    "Overview",
    "Assistant",
    "Knowledge",
    "Safety",
  ];

  return (
    <header className="header">
      <div className="logo">
        <div className="logo-mark">
          H<span>+</span>
        </div>

        <div className="logo-text">
          <strong>HEALTH.AI</strong>
          <small>INTELLIGENT HEALTH LITERACY</small>
        </div>
      </div>

      <nav className="top-navigation">
        {tabs.map((item) => (
          <button
            key={item}
            className={
              activeTab === item ? "nav-active" : ""
            }
            onClick={() => onTabChange(item)}
          >
            {item}
          </button>
        ))}
      </nav>

      <div className="header-actions">
        <div className="search">
          <span>⌕</span>
          <input placeholder="Search AI..." />
        </div>

        <button
          className="icon-button"
          aria-label="Notifications"
        >
          ◔
        </button>

        <div className="avatar">AI</div>
      </div>
    </header>
  );
}