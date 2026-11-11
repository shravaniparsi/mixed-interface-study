// Runs inside the pinned host checkout; only a disposable tpi_test database.
import fs from 'node:fs';
import { createRawDbClient } from '../lib/rawDbClient';
import { generateApiToken } from '../lib/api-tokens';

async function main() {
  const db = createRawDbClient();
  try {
    const [{ current_database: name }] = await db.$queryRawUnsafe<any[]>('SELECT current_database()');
    if (name !== 'tpi_test') throw new Error('Refusing non-scratch database');
    const [mode, output, argument] = process.argv.slice(2);
    if (mode === 'setup') {
      const admin = await db.user.findFirst({where: {access: 'ADMIN', isDeleted: false}});
      if (!admin) throw new Error('Missing seeded admin');
      await db.user.update({where: {id: admin.id}, data: {isApi: true}});
      const token = generateApiToken();
      await db.apiToken.create({data: {name: 'study-local-only', userId: admin.id, token: token.hash, tokenPrefix: token.prefix, scopes: ['client:mcp']}});
      const template = await db.repositoryCases.findFirst({where: {isDeleted: false}, orderBy: {id: 'asc'}});
      if (!template) throw new Error('Missing seeded case with valid project relations');
      const tags = [];
      for (const suffix of ['A', 'B']) tags.push(await db.tags.create({data: {name: 'study-contract-' + suffix}}));
      fs.writeFileSync(output, JSON.stringify({token: token.plaintext, userId: admin.id, template, tags}));
    } else if (mode === 'create') {
      const fixture = JSON.parse(fs.readFileSync(argument, 'utf8'));
      const {projectId, repositoryId, folderId, templateId, stateId} = fixture.template;
      const row = await db.repositoryCases.create({data: {projectId, repositoryId, folderId, templateId, stateId, creatorId: fixture.userId, name: 'study-' + output.split('/').pop(), currentVersion: 1}});
      await db.repositoryCaseTag.create({data: {caseId: row.id, tagId: fixture.tags[0].id}});
      fs.writeFileSync(output, JSON.stringify({caseId: row.id}));
    } else if (mode === 'read') {
      const caseId = Number(argument);
      const row = await db.$queryRawUnsafe<any[]>('SELECT * FROM "RepositoryCases" WHERE id=$1', caseId);
      const tags = await db.$queryRawUnsafe<any[]>('SELECT * FROM "RepositoryCaseTag" WHERE "caseId"=$1 ORDER BY "tagId"', caseId);
      const versions = await db.$queryRawUnsafe<any[]>('SELECT * FROM "RepositoryCaseVersions" WHERE "repositoryCaseId"=$1 ORDER BY version', caseId);
      fs.writeFileSync(output, JSON.stringify({row, tags, versions}));
    } else throw new Error('Unknown fixture operation');
  } finally { await db.$disconnect(); }
}
main().catch(e => { console.error(e); process.exitCode = 1; });
