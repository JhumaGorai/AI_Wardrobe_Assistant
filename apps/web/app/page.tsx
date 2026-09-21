import { getHealth } from "@/lib/api/health";

export default async function HomePage() {
  const health = await getHealth();

  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col items-center justify-center gap-4 p-8 text-center">
      <h1 className="text-3xl font-semibold">AI Wardrobe</h1>
      <p className="text-neutral-600">
        Upload your wardrobe once. Tell your AI stylist what you&apos;re dressing for.
      </p>
      <p className="text-sm text-neutral-400">
        API status:{" "}
        <span className={health.ok ? "text-green-600" : "text-red-600"}>
          {health.ok ? "connected" : "unreachable"}
        </span>
      </p>
    </main>
  );
}
