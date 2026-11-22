"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { BookOpen, Loader2, Send } from "lucide-react";
import { toast } from "sonner";
import { apiFetch, ApiError } from "@/lib/api";
import type { ChatMessage, ChatResponse, ChatSource } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Protected } from "@/components/protected";
import { DocumentPicker } from "@/components/document-picker";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";

interface DisplayMessage extends ChatMessage {
  sources?: ChatSource[];
}

function ChatContent() {
  const searchParams = useSearchParams();
  const [docId, setDocId] = useState<string | null>(
    searchParams.get("doc") ?? null
  );
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setHistoryLoading(true);
    const q = docId ? `?document_id=${docId}&limit=50` : "?limit=50";
    apiFetch<ChatMessage[]>(`/chat/history${q}`)
      .then((msgs) =>
        setMessages(
          [...msgs].sort(
            (a, b) =>
              new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
          )
        )
      )
      .catch(() => setMessages([]))
      .finally(() => setHistoryLoading(false));
  }, [docId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, asking]);

  async function ask(e: React.FormEvent) {
    e.preventDefault();
    const q = question.trim();
    if (!q || asking) return;
    setQuestion("");
    setAsking(true);
    // Show the question immediately; the answer replaces the spinner.
    const userMsg: DisplayMessage = {
      id: `temp-${Date.now()}`,
      role: "user",
      content: q,
      document_id: docId,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    try {
      const res = await apiFetch<ChatResponse>("/chat", {
        method: "POST",
        body: JSON.stringify({ question: q, document_id: docId }),
      });
      setMessages((prev) => [
        ...prev,
        {
          id: `temp-${Date.now()}-a`,
          role: "assistant",
          content: res.answer,
          document_id: res.document_id,
          created_at: new Date().toISOString(),
          sources: res.sources,
        },
      ]);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not get an answer");
      setMessages((prev) => prev.filter((m) => m.id !== userMsg.id));
    } finally {
      setAsking(false);
    }
  }

  return (
    <div className="container flex h-[calc(100vh-4rem)] flex-col py-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">Chat with your PDFs</h1>
          <p className="text-muted-foreground">
            Ask questions — answers come from your documents, with page
            citations.
          </p>
        </div>
        <div className="w-full sm:w-72">
          <DocumentPicker
            value={docId}
            onChange={setDocId}
            allowAll
            label="Ask about"
          />
        </div>
      </div>

      <Card className="mt-6 flex min-h-0 flex-1 flex-col">
        <CardContent className="flex min-h-0 flex-1 flex-col overflow-y-auto p-4">
          {historyLoading ? (
            <div className="space-y-3">
              <Skeleton className="h-16 w-3/4" />
              <Skeleton className="ml-auto h-12 w-1/2" />
              <Skeleton className="h-16 w-3/4" />
            </div>
          ) : messages.length === 0 ? (
            <div className="m-auto text-center">
              <BookOpen className="mx-auto h-10 w-10 text-muted-foreground" />
              <p className="mt-3 font-medium">No conversation yet</p>
              <p className="mt-1 text-sm text-muted-foreground">
                Ask something about{" "}
                {docId ? "this document" : "your documents"} to get started.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {messages.map((m) => (
                <div
                  key={m.id}
                  className={cn(
                    "max-w-[85%] rounded-lg px-4 py-3 text-sm leading-relaxed",
                    m.role === "user"
                      ? "ml-auto bg-primary text-primary-foreground"
                      : "bg-muted"
                  )}
                >
                  <p className="whitespace-pre-wrap">{m.content}</p>
                  {m.sources && m.sources.length > 0 && (
                    <div className="mt-3 space-y-1 border-t border-border/50 pt-2 text-xs">
                      <p className="font-semibold">Sources</p>
                      {m.sources.map((s, i) => (
                        <p key={i} className="text-muted-foreground">
                          {s.page !== null ? `Page ${s.page}: ` : ""}
                          {s.excerpt}
                        </p>
                      ))}
                    </div>
                  )}
                </div>
              ))}
              {asking && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Thinking…
                </div>
              )}
              <div ref={bottomRef} />
            </div>
          )}
        </CardContent>
        <div className="border-t p-4">
          <form onSubmit={ask} className="flex gap-2">
            <Input
              placeholder="Ask a question about your documents…"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              disabled={asking}
            />
            <Button type="submit" disabled={asking || !question.trim()}>
              {asking ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
              Ask
            </Button>
          </form>
        </div>
      </Card>
    </div>
  );
}

export default function ChatPage() {
  return (
    <Protected>
      <Suspense
        fallback={
          <div className="container space-y-4 py-8">
            <Skeleton className="h-8 w-64" />
            <Skeleton className="h-96 w-full" />
          </div>
        }
      >
        <ChatContent />
      </Suspense>
    </Protected>
  );
}
