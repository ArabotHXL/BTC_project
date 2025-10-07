import { Express } from 'express';
import swaggerUi from 'swagger-ui-express';
import * as yaml from 'yamljs';
import * as path from 'path';
import * as fs from 'fs';

export const setupSwagger = (app: Express): void => {
  const openApiPath = path.join(__dirname, '../../docs/openapi.yaml');
  
  // Check if file exists
  if (!fs.existsSync(openApiPath)) {
    const error = `❌ CRITICAL: OpenAPI spec not found at ${openApiPath}`;
    console.error(error);
    console.error('📂 Available files in __dirname:', fs.readdirSync(__dirname));
    console.error('📂 Parent directory:', fs.readdirSync(path.join(__dirname, '..')));
    
    // Throw error in development, warn in production
    if (process.env.NODE_ENV === 'development') {
      throw new Error(error);
    } else {
      console.warn('⚠️  Swagger UI will not be available');
      return;
    }
  }

  try {
    const swaggerDocument = yaml.load(openApiPath);

    app.use(
      '/api-docs',
      swaggerUi.serve,
      swaggerUi.setup(swaggerDocument, {
        customCss: '.swagger-ui .topbar { display: none }',
        customSiteTitle: 'CRM Platform API Docs',
      })
    );

    console.log('📚 Swagger UI successfully mounted at /api-docs');
    console.log(`📄 OpenAPI spec loaded from: ${openApiPath}`);
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    console.error('❌ Failed to setup Swagger UI:', errorMessage);
    
    // Throw error in development
    if (process.env.NODE_ENV === 'development') {
      throw error;
    }
  }
};
