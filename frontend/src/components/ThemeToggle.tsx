import { Moon, Sun, Monitor } from "lucide-react";
import { useTheme } from "next-themes";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export const ThemeToggle = () => {
  const { setTheme, theme = "system" } = useTheme();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="relative rounded-xl border border-border/60"
          aria-label="Toggle theme"
        >
          <Sun className="h-5 w-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
          <Moon className="absolute h-5 w-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
          <span className="sr-only">Toggle theme</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-40 rounded-xl">
        <DropdownMenuItem
          className="flex items-center gap-2"
          onClick={() => setTheme("light")}
        >
          <Sun className="h-4 w-4" />
          <span className="flex-1">Light</span>
          {theme === "light" && <span className="text-xs text-muted-foreground">Active</span>}
        </DropdownMenuItem>
        <DropdownMenuItem
          className="flex items-center gap-2"
          onClick={() => setTheme("dark")}
        >
          <Moon className="h-4 w-4" />
          <span className="flex-1">Dark</span>
          {theme === "dark" && <span className="text-xs text-muted-foreground">Active</span>}
        </DropdownMenuItem>
        <DropdownMenuItem
          className="flex items-center gap-2"
          onClick={() => setTheme("system")}
        >
          <Monitor className="h-4 w-4" />
          <span className="flex-1">System</span>
          {theme === "system" && (
            <span className="text-xs text-muted-foreground">Active</span>
          )}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
};
