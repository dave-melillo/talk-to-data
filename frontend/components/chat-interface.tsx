"use client";

import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Send, User, Bot, Loader2, BarChart2 } from "lucide-react";
import { ChartDisplay, isChartable } from "@/components/chart-display";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sql?: string;
  data?: any[];
  columns?: string[];
  rowCount?: number;
  error?: string;
  timestamp: Date;
}

interface ChatInterfaceProps {
  onQuery?: (question: string) => Promise<any>;
}

export function ChatInterface({ onQuery }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "Hello! I can help you analyze your data. Upload a CSV file or ask me a question about your data.",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch("/api/v1/queries/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: input, execute: true }),
      });

      const result = await res.json();

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: result.success 
          ? `Here's what I found:` 
          : result.error || "I couldn't generate a valid query.",
        sql: result.generated_sql,
        data: result.data,
        columns: result.columns,
        rowCount: result.row_count,
        error: result.error,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: "Sorry, there was an error processing your request.",
        error: error instanceof Error ? error.message : "Unknown error",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[600px] border rounded-lg">
      <ScrollArea ref={scrollRef} className="flex-1 p-4">
        <div className="space-y-4">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex gap-3 ${
                message.role === "user" ? "justify-end" : "justify-start"
              }`}
            >
              {message.role === "assistant" && (
                <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center shrink-0">
                  <Bot className="w-4 h-4 text-primary-foreground" />
                </div>
              )}
              
              <div
                className={`max-w-[80%] ${
                  message.role === "user" ? "items-end" : "items-start"
                }`}
              >
                <Card
                  className={`${
                    message.role === "user"
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted"
                  }`}
                >
                  <CardContent className="p-3">
                    <p className="text-sm">{message.content}</p>
                    
                    {message.sql && (
                      <div className="mt-3">
                        <p className="text-xs font-medium mb-1 opacity-70">Generated SQL:</p>
                        <pre className="bg-black/10 dark:bg-white/10 p-2 rounded text-xs overflow-x-auto">
                          <code>{message.sql}</code>
                        </pre>
                      </div>
                    )}
                    
                    {message.data && message.data.length > 0 && (
                      <div className="mt-3">
                        <p className="text-xs font-medium mb-1 opacity-70">
                          Results ({message.rowCount} rows):
                        </p>
                        <div className="overflow-x-auto">
                          <table className="w-full text-xs border-collapse">
                            <thead>
                              <tr>
                                {message.columns?.map((col) => (
                                  <th key={col} className="text-left p-1 border-b font-medium">
                                    {col}
                                  </th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {message.data.map((row, i) => (
                                <tr key={i}>
                                  {message.columns?.map((col) => (
                                    <td key={col} className="p-1 border-b border-muted">
                                      {row[col]?.toString()}
                                    </td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}
                    
                    {message.data && message.columns && isChartable(message.data, message.columns) && (
                      <div className="mt-3">
                        <ChartDisplay
                          data={message.data}
                          columns={message.columns}
                          title="Visualization"
                        />
                      </div>
                    )}
                    
                    {message.error && !message.sql && (
                      <p className="mt-2 text-xs text-red-500">
                        Error: {message.error}
                      </p>
                    )}
                  </CardContent>
                </Card>
                <span className="text-xs text-muted-foreground mt-1 px-1">
                  {message.timestamp.toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </span>
              </div>
              
              {message.role === "user" && (
                <div className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center shrink-0">
                  <User className="w-4 h-4 text-secondary-foreground" />
                </div>
              )}
            </div>
          ))}
          
          {loading && (
            <div className="flex gap-3 justify-start">
              <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center shrink-0">
                <Bot className="w-4 h-4 text-primary-foreground" />
              </div>
              <Card className="bg-muted">
                <CardContent className="p-3 flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span className="text-sm">Thinking...</span>
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      </ScrollArea>

      <form
        onSubmit={handleSubmit}
        className="p-4 border-t flex gap-2"
      >
        <Input
          placeholder="Ask a question about your data..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          className="flex-1"
          disabled={loading}
        />
        <Button type="submit" disabled={loading || !input.trim()}>
          <Send className="w-4 h-4" />
        </Button>
      </form>
    </div>
  );
}
