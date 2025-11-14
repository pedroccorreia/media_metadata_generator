
import { GoogleAuth } from 'google-auth-library';

export async function searchVAIS(query: string) {
  try {
    if (!query) {
      throw new Error('Query is required');
    }

    const auth = new GoogleAuth({
      scopes: 'https://www.googleapis.com/auth/cloud-platform',
    });
    const client = await auth.getClient();
    const accessToken = (await client.getAccessToken()).token;

    if (!accessToken) {
        throw new Error('Failed to obtain access token.');
    }

    const {
      VAIS_PROJECT_ID,
      VAIS_LOCATION,
      VAIS_COLLECTION_ID,
      VAIS_ENGINE_ID,
      VAIS_SERVING_CONFIG,
    } = process.env;

    if (!VAIS_PROJECT_ID || !VAIS_LOCATION || !VAIS_COLLECTION_ID || !VAIS_ENGINE_ID || !VAIS_SERVING_CONFIG) {
        const missingVars = [];
        if (!VAIS_PROJECT_ID) missingVars.push('VAIS_PROJECT_ID');
        if (!VAIS_LOCATION) missingVars.push('VAIS_LOCATION');
        if (!VAIS_COLLECTION_ID) missingVars.push('VAIS_COLLECTION_ID');
        if (!VAIS_ENGINE_ID) missingVars.push('VAIS_ENGINE_ID');
        if (!VAIS_SERVING_CONFIG) missingVars.push('VAIS_SERVING_CONFIG');
        throw new Error(`VAIS environment variables are not set: ${missingVars.join(', ')}`);
    }

    const url = `https://discoveryengine.googleapis.com/v1alpha/projects/${VAIS_PROJECT_ID}/locations/${VAIS_LOCATION}/collections/${VAIS_COLLECTION_ID}/engines/${VAIS_ENGINE_ID}/servingConfigs/${VAIS_SERVING_CONFIG}:search`;

    const vaisRequest = {
      query,
      pageSize: 10,
      queryExpansionSpec: {
        condition: 'AUTO',
      },
      spellCorrectionSpec: {
        mode: 'AUTO',
      },
      languageCode: 'en-US',
      userInfo: {
        timeZone: 'Australia/Sydney',
      },
    };

    // getting search results
    console.log('VAIS url: ', url)
    const vaisResponse = await fetch(url, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(vaisRequest),
    });

    if (!vaisResponse.ok) {
      const errorBody = await vaisResponse.text();
      console.error('VAIS API request failed:', errorBody);
      throw new Error(`VAIS API request failed: ${vaisResponse.statusText}`);
    }

    console.log('VAIS Response ', vaisResponse)

    const data = await vaisResponse.json();

    const results = data.results?.map((item: any) => ({
      title: item.document.derivedStructData.title,
      url: item.document.derivedStructData.url,
      snippet: item.document.derivedStructData.snippets?.[0]?.snippet,
      posterUrl: item.document.derivedStructData.poster_url,
    })) || [];

    const summary = data.summary?.summaryText || 'No summary available.';

    console.log('VAIS summary ', vaisResponse)
    console.log('VAIS results ', results.length)

    return {
      summary,
      results,
      rawResponse: data,
    };

  } catch (error: any) {
    console.error('Error in searchVAIS:', error);
    throw new Error(error.message || 'An unexpected error occurred.');
  }
}
