import * as React from "react";
import { ThemeProvider as NextThemesProvider } from "next-themes";

export interface ThemeProviderProps {
  children: React.ReactNode;
  defaultTheme?: "light" | "dark" | "system";
  storageKey?: string;
}

export const ThemeProvider = ({
  children,
  defaultTheme = "dark",
  storageKey = "aiat-theme",
}: ThemeProviderProps) => {
  return (
    <NextThemesProvider
      attribute="class"
      defaultTheme={defaultTheme}
      enableSystem
      storageKey={storageKey}
    >
      {children}
    </NextThemesProvider>
  );
};
