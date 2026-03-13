"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Settings, Eye, EyeOff, Check, AlertCircle } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

interface LLMConfig {
  provider: string;
  model: string;
  apiKey?: string;
}

const PROVIDERS = [
  {
    id: "anthropic",
    name: "Anthropic (Claude)",
    models: ["claude-sonnet-4-20250514", "claude-opus-4-20250514"],
    keyEnvVar: "ANTHROPIC_API_KEY",
  },
  {
    id: "openai",
    name: "OpenAI (GPT)",
    models: ["gpt-4o", "gpt-4-turbo"],
    keyEnvVar: "OPENAI_API_KEY",
  },
  {
    id: "google",
    name: "Google (Gemini)",
    models: ["gemini-pro", "gemini-flash"],
    keyEnvVar: "GOOGLE_API_KEY",
  },
  {
    id: "ollama",
    name: "Ollama (Local)",
    models: ["llama3.1:8b", "mistral:latest", "codellama:latest"],
    keyEnvVar: null,
  },
];

export function SettingsPanel() {
  const [config, setConfig] = useState<LLMConfig>({
    provider: "anthropic",
    model: "claude-sonnet-4-20250514",
  });
  const [showKey, setShowKey] = useState(false);
  const [saved, setSaved] = useState(false);
  const [open, setOpen] = useState(false);

  const selectedProvider = PROVIDERS.find((p) => p.id === config.provider);

  const handleSave = () => {
    // In a real app, this would save to backend or localStorage
    localStorage.setItem("ttd_llm_config", JSON.stringify(config));
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  useEffect(() => {
    const saved = localStorage.getItem("ttd_llm_config");
    if (saved) {
      try {
        setConfig(JSON.parse(saved));
      } catch {}
    }
  }, []);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          <Settings className="w-4 h-4 mr-1" />
          Settings
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>LLM Configuration</DialogTitle>
          <DialogDescription>
            Configure the AI model used for generating SQL queries.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div>
            <label className="text-sm font-medium mb-2 block">Provider</label>
            <select
              className="w-full p-2 border rounded-md bg-background"
              value={config.provider}
              onChange={(e) =>
                setConfig({
                  ...config,
                  provider: e.target.value,
                  model: PROVIDERS.find((p) => p.id === e.target.value)?.models[0] || "",
                })
              }
            >
              {PROVIDERS.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-sm font-medium mb-2 block">Model</label>
            <select
              className="w-full p-2 border rounded-md bg-background"
              value={config.model}
              onChange={(e) => setConfig({ ...config, model: e.target.value })}
            >
              {selectedProvider?.models.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </div>

          {selectedProvider?.keyEnvVar && (
            <div>
              <label className="text-sm font-medium mb-2 block">
                API Key
                <span className="text-muted-foreground ml-1">
                  (or set {selectedProvider.keyEnvVar})
                </span>
              </label>
              <div className="flex gap-2">
                <Input
                  type={showKey ? "text" : "password"}
                  placeholder="sk-..."
                  value={config.apiKey || ""}
                  onChange={(e) => setConfig({ ...config, apiKey: e.target.value })}
                />
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => setShowKey(!showKey)}
                >
                  {showKey ? (
                    <EyeOff className="w-4 h-4" />
                  ) : (
                    <Eye className="w-4 h-4" />
                  )}
                </Button>
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                Your API key is stored locally and never sent to our servers.
              </p>
            </div>
          )}

          {config.provider === "ollama" && (
            <div className="flex items-start gap-2 p-3 bg-muted rounded-lg">
              <AlertCircle className="w-4 h-4 mt-0.5 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">
                Ollama runs locally. Make sure Ollama is running on your machine
                with the selected model pulled.
              </p>
            </div>
          )}
        </div>

        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button onClick={handleSave}>
            {saved ? (
              <>
                <Check className="w-4 h-4 mr-1" />
                Saved
              </>
            ) : (
              "Save Settings"
            )}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
