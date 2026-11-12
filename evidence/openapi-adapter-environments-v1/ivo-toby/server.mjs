import { OpenAPIServer } from '@ivotoby/openapi-mcp-server';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
const server = new OpenAPIServer({ name: 'adapter-study', version: '1.0.0', apiBaseUrl: 'http://127.0.0.1:8765', openApiSpec: process.env.STUDY_SPEC, specInputMethod: 'file', transportType: 'stdio', toolsMode: 'all' });
await server.start(new StdioServerTransport());
