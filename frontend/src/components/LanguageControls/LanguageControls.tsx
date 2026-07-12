/** Модалка выбора языка при первом запуске + компактный переключатель в углу. */
import { LANGS } from "../../i18n";
import { useAppStore } from "../../store";
import "./LanguageControls.css";

/** Показывается, пока язык не выбран (lang === null). Кнопки подписаны на своих языках. */
export function LanguageModal() {
  const setLang = useAppStore((s) => s.setLang);
  return (
    <div className="lang-modal-overlay">
      <div className="lang-modal">
        <div className="lang-modal-globe">🌐</div>
        <div className="lang-modal-title">Выберите язык · Choose language · Elige idioma</div>
        <div className="lang-modal-buttons">
          {LANGS.map((l) => (
            <button key={l.code} className="lang-modal-btn" onClick={() => setLang(l.code)}>
              {l.label}
            </button>
          ))}
        </div>
        <div className="lang-modal-sub">DubaiCost · интерактивная карта стоимости недвижимости Дубая</div>
      </div>
    </div>
  );
}

/** Компактный переключатель РУ/EN/ES (левый верхний угол). */
export function LanguageSwitcher() {
  const lang = useAppStore((s) => s.lang);
  const setLang = useAppStore((s) => s.setLang);
  return (
    <div className="lang-switcher">
      {LANGS.map((l) => (
        <button
          key={l.code}
          className={`lang-btn ${lang === l.code ? "active" : ""}`}
          onClick={() => setLang(l.code)}
          title={l.label}
        >
          {l.short}
        </button>
      ))}
    </div>
  );
}
