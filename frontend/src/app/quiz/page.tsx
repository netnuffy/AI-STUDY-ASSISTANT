"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  Check,
  ChevronRight,
  Loader2,
  Plus,
  RotateCcw,
  X,
} from "lucide-react";
import { toast } from "sonner";
import { apiFetch, ApiError } from "@/lib/api";
import type {
  Quiz,
  QuizAttempt,
  QuizSubmitResponse,
  QuestionType,
} from "@/lib/types";
import { cn } from "@/lib/utils";
import { Protected } from "@/components/protected";
import { DocumentPicker } from "@/components/document-picker";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";

const TYPE_LABELS: Record<QuestionType, string> = {
  multiple_choice: "Multiple choice",
  true_false: "True / False",
  short_answer: "Short answer",
};

function QuizContent() {
  const searchParams = useSearchParams();
  const [docId, setDocId] = useState<string | null>(
    searchParams.get("doc") ?? null
  );
  const [numQuestions, setNumQuestions] = useState("10");
  const [difficulty, setDifficulty] = useState("any");
  const [types, setTypes] = useState<Record<QuestionType, boolean>>({
    multiple_choice: true,
    true_false: true,
    short_answer: true,
  });
  const [generating, setGenerating] = useState(false);
  const [quiz, setQuiz] = useState<Quiz | null>(null);
  const [answers, setAnswers] = useState<(number | string | null)[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<QuizSubmitResponse | null>(null);
  const [attempts, setAttempts] = useState<QuizAttempt[]>([]);

  const selectedTypes = (Object.keys(types) as QuestionType[]).filter(
    (t) => types[t]
  );
  const answeredCount = answers.filter((a) => a !== null && a !== "").length;

  function toggleType(t: QuestionType) {
    setTypes((prev) => ({ ...prev, [t]: !prev[t] }));
  }

  async function generate() {
    if (!docId) return;
    setGenerating(true);
    setResult(null);
    setAttempts([]);
    try {
      const question_types =
        selectedTypes.length === 0 || selectedTypes.length === 3
          ? undefined
          : selectedTypes;
      const q = await apiFetch<Quiz>(
        `/documents/${docId}/quizzes/generate`,
        {
          method: "POST",
          body: JSON.stringify({
            num_questions: Number(numQuestions),
            difficulty: difficulty === "any" ? undefined : difficulty,
            question_types,
          }),
        }
      );
      setQuiz(q);
      setAnswers(new Array(q.questions.length).fill(null));
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Generation failed");
    } finally {
      setGenerating(false);
    }
  }

  async function submit() {
    if (!quiz) return;
    setSubmitting(true);
    try {
      const res = await apiFetch<QuizSubmitResponse>(
        `/quizzes/${quiz.id}/submit`,
        {
          method: "POST",
          body: JSON.stringify({
            answers: answers.map((a) => (a === null ? "" : a)),
          }),
        }
      );
      setResult(res);
      const att = await apiFetch<QuizAttempt[]>(
        `/quizzes/${quiz.id}/attempts`
      );
      setAttempts(att);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Submit failed");
    } finally {
      setSubmitting(false);
    }
  }

  function reset() {
    setQuiz(null);
    setResult(null);
    setAnswers([]);
    setAttempts([]);
  }

  return (
    <div className="container space-y-6 py-8">
      <div>
        <h1 className="text-3xl font-bold">Quiz</h1>
        <p className="text-muted-foreground">
          Test yourself with multiple-choice, true/false and short-answer
          questions from your PDFs.
        </p>
      </div>

      {!quiz && (
        <Card>
          <CardHeader>
            <CardTitle>Generate a quiz</CardTitle>
            <CardDescription>
              Pick a document and the question mix you want.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <DocumentPicker value={docId} onChange={setDocId} />
            <div className="flex flex-wrap gap-4">
              <div className="space-y-2">
                <Label>Questions</Label>
                <Select value={numQuestions} onValueChange={setNumQuestions}>
                  <SelectTrigger className="w-32">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {["5", "10", "15", "20"].map((n) => (
                      <SelectItem key={n} value={n}>
                        {n} questions
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Difficulty</Label>
                <Select value={difficulty} onValueChange={setDifficulty}>
                  <SelectTrigger className="w-32">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="any">Mixed</SelectItem>
                    <SelectItem value="easy">Easy</SelectItem>
                    <SelectItem value="medium">Medium</SelectItem>
                    <SelectItem value="hard">Hard</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-2">
              <Label>Question types</Label>
              <div className="flex flex-wrap gap-2">
                {(Object.keys(TYPE_LABELS) as QuestionType[]).map((t) => (
                  <Button
                    key={t}
                    type="button"
                    variant={types[t] ? "default" : "outline"}
                    size="sm"
                    onClick={() => toggleType(t)}
                  >
                    {TYPE_LABELS[t]}
                  </Button>
                ))}
              </div>
              <p className="text-xs text-muted-foreground">
                All three selected (or none) means a mixed quiz.
              </p>
            </div>
            <Button onClick={generate} disabled={!docId || generating}>
              {generating ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Plus className="h-4 w-4" />
              )}
              Generate quiz
            </Button>
          </CardContent>
        </Card>
      )}

      {quiz && !result && (
        <div className="mx-auto max-w-3xl space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold">{quiz.title}</h2>
            <Badge variant="outline">
              {answeredCount} of {quiz.questions.length} answered
            </Badge>
          </div>
          {quiz.questions.map((q, i) => (
            <Card key={i}>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Badge variant="secondary">{TYPE_LABELS[q.type]}</Badge>
                  <span className="text-sm text-muted-foreground">
                    Question {i + 1}
                  </span>
                </div>
                <CardTitle className="text-base">{q.question}</CardTitle>
              </CardHeader>
              <CardContent>
                {q.options ? (
                  <div className="grid gap-2">
                    {q.options.map((opt, oi) => (
                      <Button
                        key={oi}
                        variant={answers[i] === oi ? "default" : "outline"}
                        className="justify-start"
                        onClick={() =>
                          setAnswers((prev) => {
                            const next = [...prev];
                            next[i] = oi;
                            return next;
                          })
                        }
                      >
                        {opt}
                      </Button>
                    ))}
                  </div>
                ) : (
                  <Input
                    placeholder="Type your answer…"
                    value={
                      typeof answers[i] === "string" ? (answers[i] as string) : ""
                    }
                    onChange={(e) =>
                      setAnswers((prev) => {
                        const next = [...prev];
                        next[i] = e.target.value;
                        return next;
                      })
                    }
                  />
                )}
              </CardContent>
            </Card>
          ))}
          <Button
            size="lg"
            className="w-full"
            onClick={submit}
            disabled={submitting || answeredCount < quiz.questions.length}
          >
            {submitting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
            Submit quiz
          </Button>
          <p className="text-center text-xs text-muted-foreground">
            Answer every question to submit.
          </p>
        </div>
      )}

      {quiz && result && (
        <div className="mx-auto max-w-3xl space-y-4">
          <Card>
            <CardContent className="py-8 text-center">
              <p className="text-4xl font-bold">
                {result.score} / {result.total}
              </p>
              <p className="mt-2 text-muted-foreground">
                {result.score === result.total
                  ? "Perfect score!"
                  : result.score / result.total >= 0.7
                    ? "Great work!"
                    : "Keep practising — review the explanations below."}
              </p>
              <div className="mt-6 flex justify-center gap-2">
                <Button onClick={reset}>
                  <RotateCcw className="h-4 w-4" />
                  New quiz
                </Button>
              </div>
            </CardContent>
          </Card>

          {result.results.map((r, i) => (
            <Card
              key={i}
              className={cn(
                r.is_correct ? "border-green-500/50" : "border-destructive/50"
              )}
            >
              <CardHeader>
                <div className="flex items-center gap-2">
                  {r.is_correct ? (
                    <Badge className="bg-green-600 hover:bg-green-600">
                      <Check className="h-3 w-3" /> Correct
                    </Badge>
                  ) : (
                    <Badge variant="destructive">
                      <X className="h-3 w-3" /> Incorrect
                    </Badge>
                  )}
                  <Badge variant="outline">{TYPE_LABELS[r.type]}</Badge>
                </div>
                <CardTitle className="text-base">{r.question}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-1 text-sm">
                <p>
                  <span className="font-medium">Your answer: </span>
                  {r.type === "short_answer"
                    ? String(r.selected)
                    : quiz.questions[i].options?.[Number(r.selected)] ??
                      String(r.selected)}
                </p>
                {!r.is_correct && (
                  <p>
                    <span className="font-medium">Correct answer: </span>
                    {r.type === "short_answer"
                      ? String(r.correct)
                      : quiz.questions[i].options?.[Number(r.correct)] ??
                        String(r.correct)}
                  </p>
                )}
                {r.explanation && (
                  <p className="pt-1 text-muted-foreground">{r.explanation}</p>
                )}
              </CardContent>
            </Card>
          ))}

          {attempts.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Attempt history</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-1 text-sm">
                  {attempts.map((a) => (
                    <li key={a.id} className="flex justify-between">
                      <span>
                        {new Date(a.completed_at).toLocaleString()}
                      </span>
                      <span className="font-medium">
                        {a.score} / {a.total}
                      </span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}

export default function QuizPage() {
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
        <QuizContent />
      </Suspense>
    </Protected>
  );
}
