type LanguageOption = "FR" | "EN" | "ع";

type LanguageSwitchProps = {
  value: LanguageOption;
  onChange: (value: LanguageOption) => void;
};

const options: LanguageOption[] = ["FR", "EN", "ع"];

export default function LanguageSwitch({ value, onChange }: LanguageSwitchProps) {
  return (
    <div
      className="inline-flex items-center rounded-md border border-white/25 bg-white/5 p-0.5"
      role="group"
      aria-label="Sélection de la langue"
    >
      {options.map((lang) => {
        const active = lang === value;
        return (
          <button
            key={lang}
            type="button"
            onClick={() => onChange(lang)}
            aria-pressed={active}
            className={[
              "min-w-8 rounded px-2 py-1 text-xs font-semibold transition",
              active ? "bg-white text-primary" : "text-white/90 hover:bg-white/10",
            ].join(" ")}
          >
            {lang}
          </button>
        );
      })}
    </div>
  );
}
