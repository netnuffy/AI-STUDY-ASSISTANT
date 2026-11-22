"use client";

import { useEffect, useState } from "react";
import {
  CalendarDays,
  Check,
  ChevronDown,
  ChevronUp,
  Loader2,
  Plus,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";
import { apiFetch, ApiError } from "@/lib/api";
import type {
  Paginated,
  StudyDocument,
  StudyPlan,
} from "@/lib/types";
import { cn } from "@/lib/utils";
import { Protected } from "@/components/protected";
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
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";

export default function PlannerPage() {
  const [plans, setPlans] = useState<StudyPlan[]>([]);
  const [docs, setDocs] = useState<StudyDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);

  // Create form
  const [title, setTitle] = useState("");
  const [goal, setGoal] = useState("");
  const [examDate, setExamDate] = useState("");
  const [hours, setHours] = useState(2);
  const [selectedDocs, setSelectedDocs] = useState<Set<string>>(new Set());
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    Promise.all([
      apiFetch<StudyPlan[]>("/study-plans"),
      apiFetch<Paginated<StudyDocument>>("/documents?page=1&page_size=100"),
    ])
      .then(([p, d]) => {
        setPlans(p);
        setDocs(d.items.filter((doc) => doc.status === "ready"));
      })
      .catch((err) =>
        toast.error(err instanceof ApiError ? err.message : "Could not load plans")
      )
      .finally(() => setLoading(false));
  }, []);

  function toggleDoc(id: string) {
    setSelectedDocs((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function createPlan() {
    if (!title.trim() || !goal.trim()) {
      toast.error("Give the plan a subject and a goal");
      return;
    }
    setCreating(true);
    try {
      const plan = await apiFetch<StudyPlan>("/study-plans", {
        method: "POST",
        body: JSON.stringify({
          title: title.trim(),
          goal: goal.trim(),
          exam_date: examDate || undefined,
          daily_minutes: Math.round(hours * 60),
          document_ids: Array.from(selectedDocs),
        }),
      });
      setPlans((prev) => [plan, ...prev]);
      setExpanded(plan.id);
      setTitle("");
      setGoal("");
      setExamDate("");
      setSelectedDocs(new Set());
      toast.success("Study plan created");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not create plan");
    } finally {
      setCreating(false);
    }
  }

  async function toggleTask(planId: string, taskIndex: number, done: boolean) {
    try {
      const updated = await apiFetch<StudyPlan>(
        `/study-plans/${planId}/tasks/${taskIndex}`,
        { method: "PATCH", body: JSON.stringify({ done }) }
      );
      setPlans((prev) =>
        prev.map((p) => (p.id === planId ? updated : p))
      );
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not update task");
    }
  }

  async function deletePlan(planId: string) {
    try {
      await apiFetch(`/study-plans/${planId}`, { method: "DELETE" });
      setPlans((prev) => prev.filter((p) => p.id !== planId));
      toast.success("Plan deleted");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not delete plan");
    }
  }

  return (
    <Protected>
      <div className="container space-y-6 py-8">
        <div>
          <h1 className="text-3xl font-bold">Study Planner</h1>
          <p className="text-muted-foreground">
            A day-by-day plan from now until your exam, with weekly goals and a
            revision schedule.
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Create a study plan</CardTitle>
            <CardDescription>
              Tell the AI your subject, exam date and daily hours.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="title">Subject</Label>
                <Input
                  id="title"
                  placeholder="Biology Final"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="examDate">Exam date (optional)</Label>
                <Input
                  id="examDate"
                  type="date"
                  value={examDate}
                  onChange={(e) => setExamDate(e.target.value)}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="goal">Goal</Label>
              <Textarea
                id="goal"
                placeholder="Pass the biology final with a good grade"
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="hours">Hours per day</Label>
              <Input
                id="hours"
                type="number"
                min={0.1}
                max={8}
                step={0.5}
                value={hours}
                onChange={(e) => setHours(Number(e.target.value))}
                className="w-32"
              />
            </div>
            {docs.length > 0 && (
              <div className="space-y-2">
                <Label>Documents to plan around (optional)</Label>
                <div className="flex flex-wrap gap-2">
                  {docs.map((d) => (
                    <Button
                      key={d.id}
                      type="button"
                      variant={selectedDocs.has(d.id) ? "default" : "outline"}
                      size="sm"
                      onClick={() => toggleDoc(d.id)}
                    >
                      {d.title}
                    </Button>
                  ))}
                </div>
              </div>
            )}
            <Button onClick={createPlan} disabled={creating}>
              {creating ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Plus className="h-4 w-4" />
              )}
              Create plan
            </Button>
          </CardContent>
        </Card>

        {loading ? (
          <div className="space-y-4">
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-32 w-full" />
          </div>
        ) : plans.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center text-sm text-muted-foreground">
              No study plans yet — create one above.
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            {plans.map((plan) => {
              const doneCount = plan.tasks.filter((t) => t.done).length;
              const progress = plan.tasks.length
                ? (doneCount / plan.tasks.length) * 100
                : 0;
              const open = expanded === plan.id;
              return (
                <Card key={plan.id}>
                  <CardHeader>
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div>
                        <CardTitle>{plan.title}</CardTitle>
                        <CardDescription>
                          {plan.goal}
                          {plan.exam_date && (
                            <>
                              {" · "}
                              <CalendarDays className="inline h-3 w-3" /> Exam{" "}
                              {plan.exam_date}
                            </>
                          )}
                          {" · "}
                          {plan.daily_minutes} min/day
                        </CardDescription>
                      </div>
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setExpanded(open ? null : plan.id)}
                        >
                          {open ? (
                            <ChevronUp className="h-4 w-4" />
                          ) : (
                            <ChevronDown className="h-4 w-4" />
                          )}
                          {open ? "Hide" : "View"}
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => deletePlan(plan.id)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                    <div className="flex items-center gap-3 pt-2">
                      <Progress value={progress} className="flex-1" />
                      <span className="text-xs text-muted-foreground">
                        {doneCount}/{plan.tasks.length} days done
                      </span>
                    </div>
                  </CardHeader>
                  {open && (
                    <CardContent className="space-y-6">
                      <div>
                        <h4 className="font-semibold">Daily plan</h4>
                        <ul className="mt-2 divide-y">
                          {plan.tasks.map((t, i) => (
                            <li key={i} className="flex items-center gap-3 py-2">
                              <button
                                onClick={() =>
                                  toggleTask(plan.id, i, !t.done)
                                }
                                className={cn(
                                  "flex h-5 w-5 shrink-0 items-center justify-center rounded border",
                                  t.done
                                    ? "border-primary bg-primary text-primary-foreground"
                                    : "border-input bg-background"
                                )}
                                aria-label={`Mark ${t.topic} ${t.done ? "not done" : "done"}`}
                              >
                                {t.done && <Check className="h-3 w-3" />}
                              </button>
                              <span
                                className={cn(
                                  "flex-1 text-sm",
                                  t.done && "text-muted-foreground line-through"
                                )}
                              >
                                {t.topic}
                              </span>
                              <span className="text-xs text-muted-foreground">
                                {t.date} · {t.minutes} min
                              </span>
                            </li>
                          ))}
                        </ul>
                      </div>

                      {plan.weekly_goals.length > 0 && (
                        <div>
                          <h4 className="font-semibold">Weekly goals</h4>
                          <ul className="mt-2 space-y-2">
                            {plan.weekly_goals.map((g) => (
                              <li key={g.week} className="flex gap-2 text-sm">
                                <Badge variant="outline" className="shrink-0">
                                  Week {g.week}
                                </Badge>
                                <span>{g.goal}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {plan.revision_schedule.length > 0 && (
                        <div>
                          <h4 className="font-semibold">Revision schedule</h4>
                          <ul className="mt-2 space-y-1 text-sm">
                            {plan.revision_schedule.map((r, i) => (
                              <li key={i} className="flex justify-between">
                                <span>{r.topic}</span>
                                <span className="text-muted-foreground">
                                  {r.date} · {r.minutes} min
                                </span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </CardContent>
                  )}
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </Protected>
  );
}
