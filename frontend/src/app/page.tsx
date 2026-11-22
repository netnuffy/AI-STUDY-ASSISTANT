import Link from "next/link";
import {
  ArrowRight,
  BookOpen,
  CalendarDays,
  FileText,
  Layers,
  MessageSquare,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const FEATURES = [
  {
    icon: FileText,
    title: "AI Summaries",
    description:
      "Short, standard or detailed summaries of any PDF, with key points, key concepts and questions to test yourself.",
  },
  {
    icon: MessageSquare,
    title: "Chat with your PDF",
    description:
      "Ask questions in plain language and get answers grounded in your documents, with page citations.",
  },
  {
    icon: Layers,
    title: "Flashcards",
    description:
      "Auto-generated flashcards from your material. Unknown cards resurface first, so you study what you don't know.",
  },
  {
    icon: BookOpen,
    title: "Quizzes",
    description:
      "Multiple-choice, true/false and short-answer quizzes generated from your PDFs, graded instantly.",
  },
  {
    icon: CalendarDays,
    title: "Study Planner",
    description:
      "Tell it your exam date and daily hours, and get a day-by-day plan with weekly goals and a revision schedule.",
  },
  {
    icon: Sparkles,
    title: "Progress tracking",
    description:
      "Study streaks, minutes studied, quiz scores and flashcard mastery — all in one dashboard.",
  },
];

export default function LandingPage() {
  return (
    <div>
      {/* Hero */}
      <section className="container py-16 text-center sm:py-24">
        <h1 className="mx-auto max-w-3xl text-4xl font-bold tracking-tight sm:text-5xl">
          Turn your PDFs into a personal study coach
        </h1>
        <p className="mx-auto mt-4 max-w-2xl text-lg text-muted-foreground">
          Upload your lecture notes and textbooks. Get summaries, ask
          questions, drill flashcards, take quizzes and follow a study plan —
          all generated from your own material.
        </p>
        <div className="mt-8 flex justify-center gap-3">
          <Link href="/register">
            <Button size="lg">
              Start studying free
              <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
          <Link href="/login">
            <Button size="lg" variant="outline">
              Log in
            </Button>
          </Link>
        </div>
      </section>

      {/* Features */}
      <section className="container pb-16">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map(({ icon: Icon, title, description }) => (
            <Card key={title}>
              <CardHeader>
                <Icon className="h-8 w-8 text-primary" />
                <CardTitle className="mt-2">{title}</CardTitle>
              </CardHeader>
              <CardContent>
                <CardDescription>{description}</CardDescription>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section className="border-t bg-muted/50 py-16">
        <div className="container">
          <h2 className="text-center text-2xl font-bold">How it works</h2>
          <div className="mx-auto mt-8 grid max-w-4xl gap-6 text-center sm:grid-cols-3">
            <div>
              <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-full bg-primary text-lg font-bold text-primary-foreground">
                1
              </div>
              <h3 className="mt-3 font-semibold">Upload a PDF</h3>
              <p className="mt-1 text-sm text-muted-foreground">
                Lecture notes, a textbook chapter, a research paper — up to 25
                MB each.
              </p>
            </div>
            <div>
              <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-full bg-primary text-lg font-bold text-primary-foreground">
                2
              </div>
              <h3 className="mt-3 font-semibold">AI reads it</h3>
              <p className="mt-1 text-sm text-muted-foreground">
                The text is extracted, chunked and indexed so every answer can
                point back to the page it came from.
              </p>
            </div>
            <div>
              <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-full bg-primary text-lg font-bold text-primary-foreground">
                3
              </div>
              <h3 className="mt-3 font-semibold">Study your way</h3>
              <p className="mt-1 text-sm text-muted-foreground">
                Summaries, chat, flashcards, quizzes and a plan — pick the tool
                that fits today&apos;s session.
              </p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
