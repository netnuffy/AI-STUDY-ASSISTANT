"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  Check,
  ChevronLeft,
  ChevronRight,
  Loader2,
  Plus,
  RotateCcw,
  X,
} from "lucide-react";
import { toast } from "sonner";
import { apiFetch, ApiError } from "@/lib/api";
import type { Flashcard } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Protected } from "@/components/protected";
import { DocumentPicker } from "@/components/document-picker";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";

function FlashcardsContent() {
  const searchParams = useSearchParams();
  const [docId, setDocId] = useState<string | null>(
    searchParams.get("doc") ?? null
  );
  const [cards, setCards] = useState<Flashcard[]>([]);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState<"all" | "unknown" | "known">("all");
  const [index, setIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [count, setCount] = useState(10);
  const [difficulty, setDifficulty] = useState("medium");
  const [generating, setGenerating] = useState(false);

  const load = async (id: string) => {
    setLoading(true);
    try {
      const res = await apiFetch<Flashcard[]>(`/documents/${id}/flashcards`);
      setCards(res);
      setIndex(0);
      setFlipped(false);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not load flashcards");
      setCards([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (docId) load(docId);
    else setCards([]);
  }, [docId]);

  const visible = cards.filter((c) =>
    filter === "all" ? true : filter === "known" ? c.known : !c.known
  );
  const current = visible[Math.min(index, Math.max(visible.length - 1, 0))];
  const knownCount = cards.filter((c) => c.known).length;

  async function generate() {
    if (!docId) return;
    setGenerating(true);
    try {
      const created = await apiFetch<Flashcard[]>(
        `/documents/${docId}/flashcards/generate`,
        {
          method: "POST",
          body: JSON.stringify({ count, difficulty }),
        }
      );
      toast.success(`${created.length} flashcards created`);
      load(docId);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Generation failed");
    } finally {
      setGenerating(false);
    }
  }

  async function review(known: boolean) {
    if (!current) return;
    try {
      const updated = await apiFetch<Flashcard>(
        `/flashcards/${current.id}/review`,
        { method: "PATCH", body: JSON.stringify({ known }) }
      );
      setCards((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
      setFlipped(false);
      setIndex((i) => Math.min(i + 1, visible.length - 1));
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not save review");
    }
  }

  return (
    <div className="container space-y-6 py-8">
      <div>
        <h1 className="text-3xl font-bold">Flashcards</h1>
        <p className="text-muted-foreground">
          Flip a card, then mark whether you knew it. Unknown cards come back
          first.
        </p>
      </div>

      <Card>
        <CardContent className="flex flex-wrap items-end gap-4 pt-6">
          <div className="w-full sm:w-72">
            <DocumentPicker value={docId} onChange={setDocId} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="count">New cards</Label>
            <Input
              id="count"
              type="number"
              min={1}
              max={50}
              value={count}
              onChange={(e) => setCount(Number(e.target.value))}
              className="w-24"
            />
          </div>
          <div className="space-y-2">
            <Label>Difficulty</Label>
            <Select value={difficulty} onValueChange={setDifficulty}>
              <SelectTrigger className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="easy">Easy</SelectItem>
                <SelectItem value="medium">Medium</SelectItem>
                <SelectItem value="hard">Hard</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <Button onClick={generate} disabled={!docId || generating}>
            {generating ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Plus className="h-4 w-4" />
            )}
            Generate
          </Button>
        </CardContent>
      </Card>

      {!docId ? (
        <Card>
          <CardContent className="py-12 text-center text-sm text-muted-foreground">
            Choose a document above to see its flashcards.
          </CardContent>
        </Card>
      ) : loading ? (
        <Skeleton className="h-64 w-full" />
      ) : cards.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <p className="font-medium">No flashcards for this document yet</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Generate some with the form above.
            </p>
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="flex flex-wrap items-center justify-between gap-4">
            <Tabs
              value={filter}
              onValueChange={(v) =>
                setFilter(v as "all" | "unknown" | "known")
              }
            >
              <TabsList>
                <TabsTrigger value="all">All ({cards.length})</TabsTrigger>
                <TabsTrigger value="unknown">
                  Unknown ({cards.length - knownCount})
                </TabsTrigger>
                <TabsTrigger value="known">Known ({knownCount})</TabsTrigger>
              </TabsList>
            </Tabs>
            <div className="flex items-center gap-3">
              <span className="text-sm text-muted-foreground">
                {knownCount} of {cards.length} known
              </span>
              <Progress
                value={cards.length ? (knownCount / cards.length) * 100 : 0}
                className="w-32"
              />
            </div>
          </div>

          {visible.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center text-sm text-muted-foreground">
                No cards in this filter.
              </CardContent>
            </Card>
          ) : (
            current && (
              <div className="mx-auto max-w-2xl space-y-4">
                <Card
                  className="min-h-64 cursor-pointer select-none"
                  onClick={() => setFlipped((f) => !f)}
                >
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <Badge variant="outline">{current.difficulty}</Badge>
                      <span className="text-sm text-muted-foreground">
                        {Math.min(index, visible.length - 1) + 1} /{" "}
                        {visible.length}
                      </span>
                    </div>
                  </CardHeader>
                  <CardContent className="py-8 text-center">
                    <p className="text-xs uppercase tracking-wide text-muted-foreground">
                      {flipped ? "Answer" : "Question"}
                    </p>
                    <p className="mt-3 text-xl font-medium">
                      {flipped ? current.back : current.front}
                    </p>
                    <p className="mt-6 flex items-center justify-center gap-1 text-xs text-muted-foreground">
                      <RotateCcw className="h-3 w-3" />
                      Click the card to flip
                    </p>
                  </CardContent>
                </Card>

                <div className="flex items-center justify-between">
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={() => {
                      setFlipped(false);
                      setIndex((i) => Math.max(i - 1, 0));
                    }}
                    disabled={index === 0}
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </Button>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      onClick={() => review(false)}
                      className={cn(current.known && "opacity-60")}
                    >
                      <X className="h-4 w-4" />
                      Still learning
                    </Button>
                    <Button onClick={() => review(true)}>
                      <Check className="h-4 w-4" />
                      I know this
                    </Button>
                  </div>
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={() => {
                      setFlipped(false);
                      setIndex((i) => Math.min(i + 1, visible.length - 1));
                    }}
                    disabled={index >= visible.length - 1}
                  >
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            )
          )}
        </>
      )}
    </div>
  );
}

export default function FlashcardsPage() {
  return (
    <Protected>
      <Suspense
        fallback={
          <div className="container space-y-4 py-8">
            <Skeleton className="h-8 w-64" />
            <Skeleton className="h-64 w-full" />
          </div>
        }
      >
        <FlashcardsContent />
      </Suspense>
    </Protected>
  );
}
