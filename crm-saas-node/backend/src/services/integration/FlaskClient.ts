import axios, { AxiosInstance, AxiosError } from 'axios';
import crypto from 'crypto';

interface FlaskAPIResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
}

export class FlaskClient {
  private client: AxiosInstance;
  private apiKey: string;
  private flaskBaseUrl: string;
  private signingEnabled: boolean;
  private signingSecret: string;

  constructor() {
    this.flaskBaseUrl = process.env.FLASK_BASE_URL || 'http://localhost:5000';
    this.apiKey = process.env.FLASK_API_KEY || 'hsi_dev_key_2025';
    this.signingEnabled = process.env.FLASK_REQUEST_SIGNING_ENABLED === 'true';
    this.signingSecret = process.env.FLASK_SIGNING_SECRET || process.env.SESSION_SECRET || '';

    this.client = axios.create({
      baseURL: this.flaskBaseUrl,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': this.apiKey,
      },
    });

    this.client.interceptors.request.use((config) => {
      if (this.signingEnabled && config.url && config.method) {
        let fullUrl = config.url;
        
        if (config.params && Object.keys(config.params).length > 0) {
          const queryString = new URLSearchParams(config.params).toString();
          fullUrl = `${config.url}?${queryString}`;
        }
        
        const { signature, timestamp } = this.signRequest(
          config.method.toUpperCase(),
          fullUrl,
          config.data || ''
        );
        config.headers['X-Request-Signature'] = signature;
        config.headers['X-Request-Timestamp'] = timestamp;
      }
      return config;
    });

    this.client.interceptors.response.use(
      (response) => response,
      async (error) => {
        const config = error.config;
        
        if (!config._retry && error.response?.status >= 500) {
          config._retry = (config._retry || 0) + 1;
          if (config._retry <= 2) {
            await this.sleep(1000 * config._retry);
            return this.client(config);
          }
        }
        
        return Promise.reject(error);
      }
    );
  }

  private signRequest(method: string, url: string, body: any): {
    signature: string;
    timestamp: string;
  } {
    const timestamp = Math.floor(Date.now() / 1000).toString();
    
    // 构建body字符串（匹配Flask的签名逻辑）
    let bodyStr = '';
    if (body && body !== '') {
      bodyStr = typeof body === 'string' ? body : JSON.stringify(body);
    }
    
    const message = `${method}${url}${bodyStr}${timestamp}`;
    
    const signature = crypto
      .createHmac('sha256', this.signingSecret)
      .update(message)
      .digest('hex');

    return { signature, timestamp };
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  async get<T = any>(
    endpoint: string,
    params?: any
  ): Promise<FlaskAPIResponse<T>> {
    try {
      const response = await this.client.get(endpoint, { params });

      return {
        success: true,
        data: response.data,
      };
    } catch (error) {
      return this.handleError(error);
    }
  }

  async post<T = any>(
    endpoint: string,
    data: any
  ): Promise<FlaskAPIResponse<T>> {
    try {
      const response = await this.client.post(endpoint, data);

      return {
        success: true,
        data: response.data,
      };
    } catch (error) {
      return this.handleError(error);
    }
  }

  private handleError(error: any): FlaskAPIResponse {
    if (axios.isAxiosError(error)) {
      const axiosError = error as AxiosError;
      
      if (axiosError.response) {
        const errorMessage = (axiosError.response.data as any)?.error 
          || axiosError.message
          || 'Flask API error';
        
        return {
          success: false,
          error: errorMessage,
        };
      }
      
      if (axiosError.request) {
        return {
          success: false,
          error: 'Flask service unavailable',
        };
      }
    }

    return {
      success: false,
      error: error.message || 'Unknown error',
    };
  }
}
