import { fromOpenAPI } from 'fastmcp/openapi';
const server = await fromOpenAPI({ spec: process.env.STUDY_SPEC, baseUrl: 'http://127.0.0.1:8765' });
await server.start({ transportType: 'stdio' });
