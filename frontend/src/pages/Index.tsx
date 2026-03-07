import { Layout } from '@/components/Layout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useNavigate } from 'react-router-dom';
import { LayoutDashboard, Users, BarChart3, Bot, Zap, Shield } from 'lucide-react';

const Index = () => {
  const navigate = useNavigate();

  const features = [
    {
      title: 'Live Dashboard',
      description: 'Real-time tracking of all AI agent operations, orders, and processing status.',
      icon: LayoutDashboard,
      route: '/dashboard',
    },
    {
      title: 'Human Desk',
      description: 'Review and approve agent actions with confidence scoring. Human-in-the-loop control.',
      icon: Users,
      route: '/human-desk',
    },
    {
      title: 'Agent Performance',
      description: 'Analytics and insights on agent efficiency, action breakdown, and confidence trends.',
      icon: BarChart3,
      route: '/performance',
    },
  ];

  return (
    <Layout>
      <div className="max-w-5xl mx-auto space-y-12">
        {/* Hero */}
        <div className="text-center space-y-4 pt-8">
          <div className="inline-flex items-center gap-2 bg-primary/10 text-primary px-4 py-2 rounded-full text-sm font-medium">
            <Bot className="h-4 w-4" /> AI-Powered Operations
          </div>
          <h1 className="text-4xl font-bold tracking-tight">AI Agent Operations Center</h1>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Monitor, control, and optimize your AI agents in real-time. Track every decision,
            review critical actions, and measure performance — all from one unified platform.
          </p>
          <div className="flex justify-center gap-3 pt-4">
            <Button size="lg" onClick={() => navigate('/dashboard')}>
              <LayoutDashboard className="h-4 w-4 mr-2" /> Open Dashboard
            </Button>
            <Button size="lg" variant="outline" onClick={() => navigate('/human-desk')}>
              <Shield className="h-4 w-4 mr-2" /> Human Desk
            </Button>
          </div>
        </div>

        {/* Feature Cards */}
        <div className="grid gap-6 md:grid-cols-3">
          {features.map(f => (
            <Card
              key={f.title}
              className="cursor-pointer transition-all hover:shadow-lg hover:border-primary/30"
              onClick={() => navigate(f.route)}
            >
              <CardHeader>
                <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center mb-2">
                  <f.icon className="h-5 w-5 text-primary" />
                </div>
                <CardTitle className="text-lg">{f.title}</CardTitle>
                <CardDescription>{f.description}</CardDescription>
              </CardHeader>
            </Card>
          ))}
        </div>

        {/* Capabilities */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 pb-8">
          {[
            { icon: Zap, label: 'Real-time Processing', desc: 'Live updates on all agent activities' },
            { icon: Shield, label: 'Human-in-the-Loop', desc: 'Approve or reject actions with low confidence' },
            { icon: BarChart3, label: 'Deep Analytics', desc: 'Comprehensive performance metrics and trends' },
          ].map(c => (
            <div key={c.label} className="flex items-start gap-3 p-4 rounded-lg bg-muted/50">
              <c.icon className="h-5 w-5 text-primary mt-0.5" />
              <div>
                <p className="font-medium text-sm">{c.label}</p>
                <p className="text-xs text-muted-foreground">{c.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </Layout>
  );
};

export default Index;
