import type { Metadata } from "next";
import "./globals.css";
import { ThemeProvider } from "next-themes";
import VisualEditsMessenger from "../visual-edits/VisualEditsMessenger";
import ErrorReporter from "@/components/ErrorReporter";
import Script from "next/script";
import { Toaster } from "@/components/ui/sonner";

export const metadata: Metadata = {
  title: "DocMind AI — Intelligent PDF Assistant",
  description: "Upload PDFs, ask questions, get cited answers, edit documents with AI, and manage versions — all in one premium interface.",
  keywords: "PDF, AI, RAG, document analysis, chatbot, Gemini",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="antialiased font-sans">
        <ThemeProvider
          attribute="class"
          defaultTheme="dark"
          enableSystem
          disableTransitionOnChange={false}
        >
          <Script
            id="orchids-browser-logs"
            src="https://slelguoygbfzlpylpxfs.supabase.co/storage/v1/object/public/scripts/orchids-browser-logs.js"
            strategy="afterInteractive"
            data-orchids-project-id="4f50e10c-7c35-40ad-aaee-d641d8bd08c1"
          />
          <ErrorReporter />
          <Script
            src="https://slelguoygbfzlpylpxfs.supabase.co/storage/v1/object/public/scripts//route-messenger.js"
            strategy="afterInteractive"
            data-target-origin="*"
            data-message-type="ROUTE_CHANGE"
            data-include-search-params="true"
            data-only-in-iframe="true"
            data-debug="true"
            data-custom-data='{"appName": "DocMind AI", "version": "2.0.0"}'
          />
          {children}
          <Toaster richColors position="top-right" />
          <VisualEditsMessenger />
        </ThemeProvider>
      </body>
    </html>
  );
}
