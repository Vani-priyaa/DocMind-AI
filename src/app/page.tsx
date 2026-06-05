"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { FileText, Sparkles, Shield, ChevronRight, Loader2, Brain, Zap, MessageSquare, Edit3, Download, Search } from "lucide-react";
import { login, register, getMe } from "@/lib/api";
import { toast } from "sonner";
import { ThemeToggle } from "@/components/docmind/ThemeToggle";

export default function LoginPage() {
  const router = useRouter();
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!isLogin && password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    setLoading(true);
    try {
      if (isLogin) {
        const res = await login(email, password);
        const token = res.access_token;
        localStorage.setItem("token", token);

        const user = await getMe(token);
        localStorage.setItem("user", JSON.stringify(user));

        toast.success("Welcome back to DocMind AI!");
        router.push("/docmind");
      } else {
        await register(email, password);
        toast.success("Account created! Please sign in.");
        setIsLogin(true);
      }
    } catch (err: any) {
      let errorMessage = "Authentication failed";
      if (err.response?.data?.detail) {
        if (typeof err.response.data.detail === 'string') {
          errorMessage = err.response.data.detail;
        } else if (Array.isArray(err.response.data.detail)) {
          errorMessage = err.response.data.detail.map((e: any) => e.msg).join(', ');
        }
      }
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const features = [
    { icon: Brain, title: "RAG-Powered Q&A", desc: "Ask questions, get cited answers from your PDF content" },
    { icon: MessageSquare, title: "Smart Autocomplete", desc: "AI suggests questions grounded in your document" },
    { icon: Edit3, title: "In-Chat Editing", desc: "Modify your PDF with natural language commands" },
    { icon: Search, title: "Semantic Search", desc: "Vector-powered retrieval across document chunks" },
    { icon: Download, title: "Version Control", desc: "Track changes with full revision history" },
    { icon: Zap, title: "Gemini AI", desc: "Powered by Google's most capable AI model" },
  ];

  return (
    <div className="min-h-screen bg-background flex flex-col relative overflow-hidden">
      {/* Background mesh gradient */}
      <div className="absolute inset-0 mesh-gradient opacity-60" />

      {/* Floating gradient orbs */}
      <div className="absolute top-20 left-10 w-72 h-72 rounded-full bg-primary/10 blur-3xl animate-float" />
      <div className="absolute bottom-20 right-10 w-96 h-96 rounded-full bg-chart-5/10 blur-3xl animate-float" style={{ animationDelay: "1.5s" }} />

      {/* Top Bar */}
      <header className="relative z-10 flex items-center justify-between px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center glow-primary">
            <FileText className="w-5 h-5 text-primary-foreground" />
          </div>
          <span className="text-xl font-bold tracking-tight">DocMind <span className="gradient-text">AI</span></span>
        </div>
        <ThemeToggle />
      </header>

      {/* Hero Section */}
      <div className="relative z-10 flex-1 flex flex-col items-center justify-center p-6 lg:p-12">
        <div className="max-w-7xl w-full grid lg:grid-cols-2 gap-16 items-center">

          {/* Left: Copy + Features */}
          <div className="space-y-8">
            <div className="space-y-5">
              <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-primary/10 border border-primary/20 text-sm font-medium text-primary">
                <Sparkles className="w-4 h-4" />
                AI-Powered PDF Intelligence
              </div>
              <h1 className="text-5xl lg:text-6xl xl:text-7xl font-extrabold tracking-tight leading-[1.1]">
                Your PDFs,{" "}
                <span className="gradient-text">understood.</span>
              </h1>
              <p className="text-lg text-muted-foreground max-w-xl leading-relaxed">
                Upload documents, ask questions with cited answers, edit content with natural language, 
                and manage versions — all powered by Google Gemini AI.
              </p>
            </div>

            <div className="grid sm:grid-cols-2 gap-4">
              {features.map((f, i) => (
                <div
                  key={i}
                  className="flex items-start gap-3 p-4 rounded-2xl glass-card hover:scale-[1.02] transition-all duration-300 cursor-default animate-slide-up"
                  style={{ animationDelay: `${i * 80}ms` }}
                >
                  <div className="w-9 h-9 rounded-xl bg-primary/10 flex items-center justify-center shrink-0">
                    <f.icon className="w-4.5 h-4.5 text-primary" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-sm">{f.title}</h3>
                    <p className="text-xs text-muted-foreground mt-0.5">{f.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Right: Auth Card */}
          <div className="flex justify-center lg:justify-end">
            <Card className="w-full max-w-md glass-card shadow-2xl border-0">
              <CardHeader className="space-y-1 pb-4">
                <CardTitle className="text-2xl font-bold tracking-tight">
                  {isLogin ? "Welcome back" : "Create account"}
                </CardTitle>
                <CardDescription>
                  {isLogin ? "Sign in to access your document workspace" : "Get started with DocMind AI"}
                </CardDescription>
              </CardHeader>
              <form onSubmit={handleSubmit}>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Input
                      id="login-email"
                      type="email"
                      placeholder="Email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                      className="h-12 rounded-xl bg-background/50"
                    />
                  </div>
                  <div className="space-y-2">
                    <Input
                      id="login-password"
                      type="password"
                      placeholder="Password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      className="h-12 rounded-xl bg-background/50"
                    />
                  </div>
                  {!isLogin && (
                    <div className="space-y-2">
                      <Input
                        id="confirm-password"
                        type="password"
                        placeholder="Confirm Password"
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        required
                        className="h-12 rounded-xl bg-background/50"
                      />
                    </div>
                  )}
                  {error && <p className="text-sm text-destructive font-medium">{error}</p>}
                </CardContent>
                <CardFooter className="flex flex-col space-y-4">
                  <Button
                    id="login-submit"
                    className="w-full h-12 rounded-xl text-base font-semibold glow-primary"
                    type="submit"
                    disabled={loading}
                  >
                    {loading ? (
                      <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                    ) : (
                      isLogin ? "Sign In" : "Create Account"
                    )}
                    <ChevronRight className="ml-2 h-4 w-4" />
                  </Button>
                  <button
                    type="button"
                    onClick={() => {
                      setIsLogin(!isLogin);
                      setError("");
                    }}
                    className="text-sm text-muted-foreground hover:text-primary transition-colors"
                  >
                    {isLogin ? "Don't have an account? Sign up" : "Already have an account? Sign in"}
                  </button>
                </CardFooter>
              </form>
            </Card>
          </div>
        </div>
      </div>

      <footer className="relative z-10 p-6 text-center text-xs text-muted-foreground border-t border-border/50">
        &copy; 2026 DocMind AI. Powered by Google Gemini &amp; RAG Technology.
      </footer>
    </div>
  );
}
