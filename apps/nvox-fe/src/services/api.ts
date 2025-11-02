import {
  SignupRequest,
  SignupResponse,
  LoginRequest,
  LoginResponse,
  JourneyState,
  SubmitAnswerRequest,
  SubmitAnswerResponse,
  ApiError,
  JourneyHistoryResponse,
  StageDetailsResponse,
} from '../types/api';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class ApiClient {
  private baseUrl: string;
  private token: string | null = null;
  private onUnauthorizedCallback: (() => void) | null = null;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
    // Try to restore token from localStorage
    this.token = localStorage.getItem('access_token');
  }

  setOnUnauthorized(callback: () => void) {
    this.onUnauthorizedCallback = callback;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };

    if (this.token && !endpoint.includes('/signup') && !endpoint.includes('/login')) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      // Handle 401 Unauthorized - but skip for login/signup endpoints
      if (response.status === 401 && !endpoint.includes('/login') && !endpoint.includes('/signup')) {
        this.logout();
        if (this.onUnauthorizedCallback) {
          this.onUnauthorizedCallback();
        }
        throw new Error('Session expired. Please login again.');
      }

      const error: ApiError = await response.json();
      throw new Error(error.detail || 'An error occurred');
    }

    return response.json();
  }

  // Authentication
  async signup(data: SignupRequest): Promise<SignupResponse> {
    const response = await this.request<SignupResponse>('/v1/signup', {
      method: 'POST',
      body: JSON.stringify(data),
    });

    // Store email for display
    localStorage.setItem('user_email', data.email);

    return response;
  }

  async login(data: LoginRequest): Promise<LoginResponse> {
    const response = await this.request<LoginResponse>('/v1/login', {
      method: 'POST',
      body: JSON.stringify(data),
    });

    // Store token and email
    this.token = response.access_token;
    localStorage.setItem('access_token', response.access_token);
    localStorage.setItem('user_id', response.user_id);
    localStorage.setItem('user_email', data.email);

    return response;
  }

  logout() {
    this.token = null;
    localStorage.removeItem('access_token');
    localStorage.removeItem('user_id');
    localStorage.removeItem('user_email');
  }

  getUserEmail(): string | null {
    return localStorage.getItem('user_email');
  }

  isAuthenticated(): boolean {
    return !!this.token;
  }

  // Journey endpoints
  async getCurrentJourney(): Promise<JourneyState> {
    return this.request<JourneyState>('/v1/journey/current');
  }

  async submitAnswer(data: SubmitAnswerRequest): Promise<SubmitAnswerResponse> {
    return this.request<SubmitAnswerResponse>('/v1/journey/answer', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async continueJourney(): Promise<SubmitAnswerResponse> {
    return this.request<SubmitAnswerResponse>('/v1/journey/continue', {
      method: 'POST',
    });
  }

  async deleteUser(): Promise<{ success: boolean; message: string }> {
    return this.request('/v1/user', {
      method: 'DELETE',
    });
  }

  // Journey History endpoints
  async getJourneyHistory(): Promise<JourneyHistoryResponse> {
    return this.request<JourneyHistoryResponse>('/v1/journey/history');
  }

  async getStageDetails(stageId: string): Promise<StageDetailsResponse> {
    return this.request<StageDetailsResponse>(`/v1/journey/stage/${stageId}`);
  }
}

export const apiClient = new ApiClient();
