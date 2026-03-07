export type OrderStatus = 'pending' | 'in_progress' | 'completed' | 'failed';
export type ActionType = 'email_sent' | 'data_updated' | 'escalated' | 'api_call' | 'notification' | 'verification';
export type ReviewStatus = 'pending' | 'approved' | 'rejected';

export interface AgentThought {
  id: string;
  timestamp: string;
  thought: string;
  reasoning: string;
  confidence: number;
}

export interface AgentAction {
  id: string;
  type: ActionType;
  description: string;
  timestamp: string;
  status: OrderStatus;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  confidence: number;
}

export interface PipelineStep {
  id: string;
  agentName: string;
  status: 'completed' | 'failed' | 'skipped';
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  summary: string;
}

export interface Order {
  id: string;
  title: string;
  description: string;
  status: OrderStatus;
  agentId: string;
  agentName: string;
  createdAt: string;
  updatedAt: string;
  thoughts: AgentThought[];
  actions: AgentAction[];
  inputData: Record<string, unknown>;
  outputData: Record<string, unknown>;
  pipelineSteps?: PipelineStep[];
}

export interface ShipmentDetails {
  carrier?: string;
  weather?: string;
  priority?: string;
  isDelayed?: boolean;
  etaHours?: number;
  warehouseLoad?: number;
  trafficDelay?: number;
  delayProbability?: number;
  riskLevel?: string;
  riskScore?: number;
  rootCauses?: string[];
  recommendedAction?: string;
  triggeredRules?: string[];
}

export interface HumanReviewItem {
  id: string;
  orderId: string;
  orderTitle: string;
  action: AgentAction;
  agentReasoning: string;
  confidence: number;
  status: ReviewStatus;
  createdAt: string;
  reviewedAt?: string;
  reviewedBy?: string;
  shipmentDetails?: ShipmentDetails;
}

export interface PerformanceData {
  totalOrders: number;
  autoCompleted: number;
  humanInLoop: number;
  failedOrders: number;
  avgConfidence: number;
  avgProcessingTime: number;
  actionBreakdown: { type: ActionType; count: number }[];
  dailyPerformance: { date: string; completed: number; failed: number; humanReview: number }[];
  confidenceDistribution: { range: string; count: number }[];
}
