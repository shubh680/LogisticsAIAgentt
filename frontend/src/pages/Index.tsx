import { Layout } from '@/components/Layout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  Users,
  BarChart3,
  Bot,
  Sparkles,
  Zap,
  Shield,
  ArrowRight,
  Clock3,
  Activity,
  CheckCircle2,
  Radar,
  Workflow,
  Gauge,
  BellRing,
} from 'lucide-react';

const Index = () => {
  const navigate = useNavigate();

  const features = [
    {
      title: 'Live Dashboard',
      description: 'Real-time tracking of all AI agent operations, orders, and processing status.',
      icon: LayoutDashboard,
      route: '/dashboard',
      stat: 'Real-time events',
    },
    {
      title: 'Human Desk',
      description: 'Review and approve agent actions with confidence scoring. Human-in-the-loop control.',
      icon: Users,
      route: '/human-desk',
      stat: 'Critical actions queue',
    },
    {
      title: 'Agent Performance',
      description: 'Analytics and insights on agent efficiency, action breakdown, and confidence trends.',
      icon: BarChart3,
      route: '/performance',
      stat: 'Confidence + throughput',
    },
  ];

  const quickStats = [
    { label: 'Decision Loop', value: '< 3s', icon: Clock3 },
    { label: 'Signal Streams', value: '7+', icon: Activity },
    { label: 'Control Layer', value: 'Human-in-loop', icon: Shield },
    { label: 'Automation', value: 'Policy-first', icon: CheckCircle2 },
  ];

  const signalFeed = [
    { label: 'Firebase Ingestion', value: 'Live', tone: 'text-green-600' },
    { label: 'Risk Engine', value: 'Healthy', tone: 'text-primary' },
    { label: 'Human Desk Queue', value: '2 pending', tone: 'text-amber-600' },
    { label: 'Policy Checks', value: 'Running', tone: 'text-primary' },
  ];

  return (
    <Layout>
      <div className="mx-auto max-w-6xl space-y-8 pb-4">
        <section className="relative overflow-hidden rounded-3xl border bg-card p-6 md:p-10">
          <div className="home-grid-overlay pointer-events-none absolute inset-0" />
          <div className="home-orb home-orb-left pointer-events-none" />
          <div className="home-orb home-orb-right pointer-events-none" />

          <div className="relative z-10 grid gap-8 lg:grid-cols-[1.35fr_1fr] lg:items-center">
            <div className="space-y-5">
              <Badge className="w-fit gap-2 border border-primary/30 bg-primary/10 px-3 py-1 text-primary hover:bg-primary/10">
                <Sparkles className="h-4 w-4" /> Logistics AI Mission Control
              </Badge>
              <div className="space-y-3">
                <h1 className="text-balance text-3xl font-bold leading-tight tracking-tight md:text-5xl">
                  Where Autonomous Decisions Meet Human Oversight
                </h1>
                <p className="max-w-2xl text-pretty text-sm leading-relaxed text-muted-foreground md:text-base">
                  Command ingestion, delay prediction, policy enforcement, and human approvals from one
                  intelligent surface built for high-stakes logistics operations.
                </p>
              </div>
              <div className="flex flex-wrap gap-3">
                <Button size="lg" className="gap-2" onClick={() => navigate('/dashboard')}>
                  Open Dashboard <ArrowRight className="h-4 w-4" />
                </Button>
                <Button size="lg" variant="outline" className="gap-2" onClick={() => navigate('/human-desk')}>
                  Review Queue <BellRing className="h-4 w-4" />
                </Button>
                <Button size="lg" variant="secondary" className="gap-2" onClick={() => navigate('/performance')}>
                  Performance <BarChart3 className="h-4 w-4" />
                </Button>
              </div>
            </div>

            <div className="space-y-3">
              <div className="home-reveal rounded-2xl border bg-background/80 p-4 backdrop-blur-sm">
                <div className="mb-3 flex items-center justify-between">
                  <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">System Pulse</p>
                  <Radar className="h-4 w-4 text-primary" />
                </div>
                <div className="space-y-2">
                  {signalFeed.map(item => (
                    <div key={item.label} className="flex items-center justify-between rounded-lg border bg-card px-3 py-2">
                      <span className="text-xs text-muted-foreground">{item.label}</span>
                      <span className={`text-xs font-semibold ${item.tone}`}>{item.value}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                {quickStats.map(stat => (
                  <div key={stat.label} className="home-reveal rounded-xl border bg-background/70 p-3">
                    <div className="flex items-start justify-between">
                      <p className="text-[11px] uppercase tracking-wide text-muted-foreground">{stat.label}</p>
                      <stat.icon className="h-4 w-4 text-primary" />
                    </div>
                    <p className="mt-1 text-base font-semibold leading-tight">{stat.value}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="grid gap-4 md:grid-cols-3">
          {features.map(f => (
            <Card
              key={f.title}
              className="group cursor-pointer border-border/80 bg-card/85 transition-all duration-300 hover:-translate-y-1 hover:border-primary/50 hover:shadow-lg"
              onClick={() => navigate(f.route)}
            >
              <CardHeader>
                <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-lg bg-primary/10 transition-colors group-hover:bg-primary/20">
                  <f.icon className="h-5 w-5 text-primary" />
                </div>
                <CardTitle className="text-lg leading-tight">{f.title}</CardTitle>
                <CardDescription>{f.description}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between rounded-md border bg-muted/30 px-3 py-2 text-xs">
                  <span className="text-muted-foreground">{f.stat}</span>
                  <ArrowRight className="h-3.5 w-3.5 text-primary transition-transform group-hover:translate-x-0.5" />
                </div>
              </CardContent>
            </Card>
          ))}
        </section>

        <section className="rounded-3xl border bg-card p-5 md:p-6">
          <div className="mb-5 flex items-center justify-between gap-2">
            <h2 className="text-lg font-semibold">Operational Flow</h2>
            <Badge variant="secondary" className="gap-1 text-xs"><Workflow className="h-3.5 w-3.5" /> End-to-end visibility</Badge>
          </div>
          <div className="grid gap-3 md:grid-cols-3">
            {[
              {
                icon: Zap,
                label: 'Ingest + Predict',
                desc: 'Live shipment signals and ML delay probabilities are combined in real time.',
              },
              {
                icon: Shield,
                label: 'Reason + Policy',
                desc: 'Risk reasoning and policy checks decide auto-action vs manual review.',
              },
              {
                icon: BarChart3,
                label: 'Review + Improve',
                desc: 'Human decisions and performance metrics create a continuous learning loop.',
              },
            ].map(c => (
              <div key={c.label} className="home-reveal rounded-xl border bg-background p-4">
                <div className="mb-2 flex h-9 w-9 items-center justify-center rounded-md bg-primary/10">
                  <c.icon className="h-4 w-4 text-primary" />
                </div>
                <p className="text-sm font-semibold">{c.label}</p>
                <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{c.desc}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-2xl border bg-gradient-to-r from-muted/60 via-card to-muted/40 p-5 md:p-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="text-xs uppercase tracking-wider text-muted-foreground">Next best action</p>
              <h3 className="mt-1 text-xl font-semibold">Start a full analysis run and review high-risk shipments first</h3>
              <p className="mt-1 text-sm text-muted-foreground">The platform will auto-prioritize risky routes and push only uncertain cases to Human Desk.</p>
            </div>
            <Button size="lg" className="gap-2" onClick={() => navigate('/dashboard')}>
              Launch Analysis <Gauge className="h-4 w-4" />
            </Button>
          </div>
        </section>
      </div>
    </Layout>
  );
};

export default Index;
