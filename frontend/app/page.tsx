"use client";

import { useState } from "react";
import { ChatInterface } from "@/components/chat-interface";
import { FileUpload } from "@/components/file-upload";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Database, MessageSquare, Upload } from "lucide-react";

export default function Home() {
  const [activeTab, setActiveTab] = useState("chat");

  return (
    <main className="min-h-screen bg-background">
      <div className="container mx-auto py-8 px-4 max-w-5xl">
        <header className="text-center mb-8">
          <h1 className="text-4xl font-bold mb-2">Talk To Data</h1>
          <p className="text-muted-foreground">
            Ask questions about your data in plain English
          </p>
        </header>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-2 mb-6">
            <TabsTrigger value="chat" className="flex items-center gap-2">
              <MessageSquare className="w-4 h-4" />
              Chat
            </TabsTrigger>
            <TabsTrigger value="upload" className="flex items-center gap-2">
              <Upload className="w-4 h-4" />
              Upload Data
            </TabsTrigger>
          </TabsList>

          <TabsContent value="chat">
            <ChatInterface />
          </TabsContent>

          <TabsContent value="upload">
            <FileUpload />
          </TabsContent>
        </Tabs>
      </div>
    </main>
  );
}
