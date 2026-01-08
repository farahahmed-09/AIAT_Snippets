import { Check } from "lucide-react";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";

interface BrandingTabProps {
  selectedIntro: string | null;
  selectedOutro: string | null;
  onSelectIntro: (id: string | null) => void;
  onSelectOutro: (id: string | null) => void;
  applyToAll: boolean;
  onApplyToAllChange: (value: boolean) => void;
}

export const BrandingTab = ({
  selectedIntro,
  selectedOutro,
  onSelectIntro,
  onSelectOutro,
  applyToAll,
  onApplyToAllChange,
}: BrandingTabProps) => {
  const intros = brandingTemplates.filter((t) => t.type === "intro");
  const outros = brandingTemplates.filter((t) => t.type === "outro");

  const TemplateCard = ({
    template,
    isSelected,
    onClick,
  }: {
    template: BrandingTemplate;
    isSelected: boolean;
    onClick: () => void;
  }) => (
    <button
      onClick={onClick}
      className={`relative aspect-video rounded-xl overflow-hidden transition-all duration-200 ${
        isSelected
          ? "ring-2 ring-primary ring-offset-2 ring-offset-background"
          : "hover:scale-105"
      }`}
    >
      {/* Gradient Background */}
      <div className={`absolute inset-0 bg-gradient-to-br ${template.color}`} />

      {/* Template Name */}
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-white text-sm font-medium text-center px-2">
          {template.name}
        </span>
      </div>

      {/* Selected Checkmark */}
      {isSelected && (
        <div className="absolute top-2 right-2 w-6 h-6 rounded-full bg-primary flex items-center justify-center">
          <Check className="w-4 h-4 text-primary-foreground" />
        </div>
      )}
    </button>
  );

  return (
    <div className="space-y-6">
      {/* Apply to All Toggle */}
      <div className="glass rounded-xl p-4 flex items-center justify-between">
        <div>
          <Label htmlFor="apply-all" className="font-medium">
            Apply to all clips
          </Label>
          <p className="text-xs text-muted-foreground mt-1">
            Use selected templates for every exported clip
          </p>
        </div>
        <Switch
          id="apply-all"
          checked={applyToAll}
          onCheckedChange={onApplyToAllChange}
        />
      </div>

      {/* Intros Section */}
      <div>
        <h4 className="text-sm font-semibold mb-3 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full ai-gradient" />
          Intro Templates
        </h4>
        <div className="grid grid-cols-2 gap-3">
          {intros.map((template) => (
            <TemplateCard
              key={template.id}
              template={template}
              isSelected={selectedIntro === template.id}
              onClick={() =>
                onSelectIntro(
                  selectedIntro === template.id ? null : template.id
                )
              }
            />
          ))}
        </div>
      </div>

      {/* Outros Section */}
      <div>
        <h4 className="text-sm font-semibold mb-3 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full ai-gradient" />
          Outro Templates
        </h4>
        <div className="grid grid-cols-2 gap-3">
          {outros.map((template) => (
            <TemplateCard
              key={template.id}
              template={template}
              isSelected={selectedOutro === template.id}
              onClick={() =>
                onSelectOutro(
                  selectedOutro === template.id ? null : template.id
                )
              }
            />
          ))}
        </div>
      </div>

      {/* No Selection Note */}
      {!selectedIntro && !selectedOutro && (
        <p className="text-xs text-muted-foreground text-center py-2">
          Select templates to add professional intros and outros to your clips
        </p>
      )}
    </div>
  );
};
