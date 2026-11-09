// Exact submitted commands and a bounded, explicit API-visible state projection.
import {isDeepStrictEqual} from 'node:util';

export const SNAPSHOT_SCOPE = 'current user public fields, complete own-article list, global tag membership, and comments on every listed article; excludes auth tokens, not timestamps';

export function command(method, path, payload = null) {
  if (!['POST', 'PUT', 'DELETE'].includes(method) || !path.startsWith('/api/')) throw new Error('Unsupported command');
  return {method, path, payload};
}

export function audit(name, stage, source, expected, observed) {
  return {name, stage, source, expected, observed, passed: isDeepStrictEqual(expected, observed)};
}

export function enforce(record) {
  if (!record.passed) {
    const error = new Error('Operation not comparable: ' + record.name);
    error.name = 'OperationNotComparable';
    throw error;
  }
}

export function profileBundle(user, bio) {
  if (typeof user?.username !== 'string' || typeof user?.email !== 'string') throw new Error('Missing bound user fields');
  const result = {username: user.username, email: user.email, bio};
  if (user.image !== null && user.image !== undefined) result.image = user.image;
  return {user: result};
}

export function profileForm(user) {
  return {username: user.username, email: user.email, bio: user.bio ?? '', image: user.image ?? '', new_credential_blank: true};
}

export function articleIdentity(article) {
  return {slug: article?.slug, title: article?.title, description: article?.description,
    body: article?.body, tagList: [...new Set(article?.tagList || [])].sort(), author: article?.author?.username};
}

export function commentIdentity(comment) {
  return {id: comment?.id, body: comment?.body, author: comment?.author?.username};
}

export function commentPath(slug, id) {
  if (typeof slug !== 'string' || !slug || !Number.isSafeInteger(id) || id <= 0) throw new Error('Invalid returned comment binding');
  return `/api/articles/${encodeURIComponent(slug)}/comments/${id}`;
}

export function projectSnapshot(reads) {
  const at = path => {
    const values = reads.filter(r => r.path === path);
    if (values.length !== 1 || values[0].status !== 200) throw new Error('Missing, duplicate or unreadable snapshot probe: ' + path);
    return values[0].data;
  };
  const rawUser = at('/api/user')?.user;
  if (!rawUser || ['username', 'email', 'bio', 'image'].some(k => !(k in rawUser))) throw new Error('Incomplete current user');
  const user = Object.fromEntries(['username', 'email', 'bio', 'image'].map(k => [k, rawUser[k]]));
  const collection = at('/api/articles?author=pilotresearch');
  const tags = at('/api/tags')?.tags;
  if (!Array.isArray(tags) || tags.some(t => typeof t !== 'string')) throw new Error('Invalid tag collection');
  if (!Array.isArray(collection?.articles) || !Number.isSafeInteger(collection.articlesCount)
      || collection.articlesCount !== collection.articles.length) throw new Error('Partial or invalid article collection');
  const seen = new Set();
  const articles = collection.articles.map(article => {
    if (typeof article?.slug !== 'string' || !article.slug || seen.has(article.slug)
        || !Array.isArray(article.tagList) || article.tagList.some(t => typeof t !== 'string')) throw new Error('Invalid article identity or tags');
    seen.add(article.slug);
    const comments = at(`/api/articles/${encodeURIComponent(article.slug)}/comments`)?.comments;
    if (!Array.isArray(comments)) throw new Error('Invalid comment collection');
    const ids = new Set();
    for (const c of comments) {
      if (!Number.isSafeInteger(c.id) || c.id <= 0 || ids.has(c.id)) throw new Error('Invalid or duplicate comment identity');
      ids.add(c.id);
    }
    return {article: {...article, tagList: [...new Set(article.tagList)].sort()},
      comments: [...comments].sort((a, b) => a.id - b.id)};
  }).sort((a, b) => a.article.slug < b.article.slug ? -1 : a.article.slug > b.article.slug ? 1 : 0);
  if (reads.length !== 3 + articles.length) throw new Error('Unregistered snapshot probes');
  return {user, articles, tags: [...new Set(tags)].sort()};
}

export async function snapshot(read) {
  const reads = [];
  try {
    async function get(path) {
      const response = await read('GET', path);
      reads.push({path, status: response.status, data: response.data, response_sequence: response.response_sequence});
      return response;
    }
    await get('/api/user');
    const list = await get('/api/articles?author=pilotresearch');
    await get('/api/tags');
    if (list.status !== 200 || !Array.isArray(list.data?.articles)) throw new Error('Article list unreadable');
    for (const a of list.data.articles) {
      if (typeof a?.slug !== 'string' || !a.slug) throw new Error('Article has no readable reference');
      await get(`/api/articles/${encodeURIComponent(a.slug)}/comments`);
    }
    return {scope: SNAPSHOT_SCOPE, readable: true, reads, data: projectSnapshot(reads)};
  } catch (error) {
    return {scope: SNAPSHOT_SCOPE, readable: false, reads, error: error.message};
  }
}

export function rejectionState(before, after) {
  if (!before || !after) return 'unobserved';
  if (!before.readable || !after.readable) return 'unreadable';
  return isDeepStrictEqual(before.data, after.data) ? 'unchanged' : 'changed';
}
