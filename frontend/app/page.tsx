"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function Home() {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;

    setLoading(true);
    try {
      const res = await fetch("/api/v1/queries/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, execute: true }),
      });
      const data = await res.json();
      setResult(data);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-background">
      <div className="container mx-auto py-8 px-4">
        <h1 className="text-4xl font-bold text-center mb-2">Talk To Data</h1>
        <p className="text-muted-foreground text-center mb-8">
          Ask questions about your data in plain English
        </p>

        <Card className="max-w-3xl mx-auto">
          <CardHeader>
            <CardTitle>Ask a Question</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="flex gap-2">
              <Input
                placeholder="e.g., What are my top 10 customers?"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                className="flex-1"
              />
              <Button type="submit" disabled={loading}>
                {loading ? "Generating..." : "Ask"}
              </Button>
            </form>
          </CardContent>
        </Card>

        {result && (
          <Card className="max-w-3xl mx-auto mt-6">
            <CardHeader>
              <CardTitle>Result</CardTitle>
            </CardHeader>
            <CardContent>
              {result.generated_sql && (
                <div className="mb-4">
                  <h3 className="font-semibold mb-2">Generated SQL:</h3>
                  <pre className="bg-muted p-4 rounded-lg overflow-x-auto text-sm">
                    <code>{result.generated_sql}</code>
                  </pre>
                </div>
              )}
              
              {result.data && (
                <div>
                  <h3 className="font-semibold mb-2">
                    Results ({result.row_count} rows):
                  </h3>
                  <pre className="bg-muted p-4 rounded-lg overflow-x-auto text-sm max-h-96">
                    <code>{JSON.stringify(result.data, null, 2)}</code>
                  </pre>
                </div>
              )}

              {result.error && (
                <div className="text-red-600">
                  Error: {result.error}
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </main>
  );
}
