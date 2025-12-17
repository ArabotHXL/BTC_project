import { FlaskClient } from './FlaskClient';

export class IntelligenceService {
  private flaskClient: FlaskClient;

  constructor() {
    this.flaskClient = new FlaskClient();
  }

  async getForecast() {
    const response = await this.flaskClient.get('/api/intelligence/forecast');
    return response.success ? response.data : null;
  }

  async getOptimize() {
    const response = await this.flaskClient.get('/api/intelligence/optimize');
    return response.success ? response.data : null;
  }

  async getExplain() {
    const response = await this.flaskClient.get('/api/intelligence/explain');
    return response.success ? response.data : null;
  }

  async getHealth() {
    const response = await this.flaskClient.get('/api/intelligence/health');
    return response.success ? response.data : null;
  }
}
