import Link from 'next/link'; // Restored original Next.js import
import Image from 'next/image'; // Restored original Next.js import
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Link as LinkIcon, FileText, Beaker } from 'lucide-react';
import {
    Accordion,
    AccordionContent,
    AccordionItem,
    AccordionTrigger,
} from '@/components/ui/accordion';

// Restored original API import
// NOTE: This file must exist in '@/lib/api' for a successful Next.js build.
import { search } from '@/lib/api'; 

interface SearchPageProps {
  searchParams: {
    q?: string | string[];
  };
}

/**
 * Renders the search results page, fetching real data via the 'search' utility.
 * @param {SearchPageProps} { searchParams }
 * @returns {JSX.Element}
 */
export default async function SearchPage({ searchParams }: SearchPageProps) {
  // Extract and clean the query string, defaulting to an empty string.
  const query = (Array.isArray(searchParams.q) ? searchParams.q[0] : searchParams.q) || '';

  if (!query) {
    return (
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="text-center">
          <h1 className="text-4xl font-bold text-gray-800 dark:text-gray-100">Search</h1>
          <p className="mt-4 text-muted-foreground">
            Please enter a search query to begin your research.
          </p>
        </div>
      </div>
    );
  }

  let summary = '';
  let results: any[] = [];
  let rawResponse = null;

  try {
    // Calling the actual search function
    const searchResult = await search(query); 
    summary = searchResult.summary;
    results = searchResult.results;
    rawResponse = searchResult.rawResponse;
  } catch (err) {
    console.error("Error fetching search results:", err);
    summary = 'An error occurred while fetching search results.';
    results = [];
    rawResponse = null;
  }

  return (
    <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="mb-8">
        <h1 className="text-3xl font-extrabold tracking-tight text-gray-800 dark:text-gray-100">
          Search Results for &quot;{query}&quot;
        </h1>
      </div>

       <div className="space-y-10">
         {/* AI Summary Card */}
         <Card className="shadow-lg border-t-4 border-indigo-500">
            <CardHeader>
              <CardTitle className="text-xl font-semibold flex items-center gap-2">
                <FileText className="h-5 w-5 text-indigo-500" />
                AI Summary
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-700 dark:text-gray-300 leading-relaxed">{summary}</p>
            </CardContent>
          </Card>
        
        {/* References Section */}
        <div>
          <h2 className="text-2xl font-bold tracking-tight mb-6 text-gray-800 dark:text-gray-100">
            References Found
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {results.map((result, index) => (
                // Use file_name as key, falling back to index
                <Card key={result.file_name || index} className="flex flex-col overflow-hidden transition-all duration-300 hover:shadow-xl">
                    {result.posterUrl && (
                        <div className="relative aspect-video w-full">
                            {/* Restored Next.js <Image> */}
                            <Image 
                                src={result.posterUrl}
                                alt={`Poster for ${result.file_name}`}
                                fill
                                data-ai-hint="movie poster"
                                className="object-cover transition-opacity duration-500"
                            />
                        </div>
                    )}
                    <CardHeader className="p-4 border-b dark:border-gray-700">
                        <CardTitle className="text-lg leading-snug">
                             {/* Restored Next.js <Link> */}
                             <Link
                                href={result.file_name}
                                // Note: Target/rel attributes are generally set on the <a> tag rendered by Link
                                className="group flex items-start gap-2 text-indigo-600 hover:text-indigo-800 dark:text-indigo-400 dark:hover:text-indigo-200 transition-colors"
                                >
                                <LinkIcon className="h-4 w-4 mt-1 flex-shrink-0" />
                                <span className="line-clamp-2">
                                    {result.file_name}
                                </span>
                            </Link>
                        </CardTitle>
                    </CardHeader>
                    
                    <CardContent className="flex-grow p-4">
                      {result.snippet && (
                        <div className="flex gap-3 items-start text-sm text-gray-500 dark:text-gray-400">
                            <FileText className="h-4 w-4 mt-0.5 flex-shrink-0 text-indigo-500"/>
                            {/* Snippet displays sanitized HTML content */}
                            <p className="italic" dangerouslySetInnerHTML={{ __html: result.snippet }} />
                        </div>
                      )}
                    </CardContent>
                </Card>
            ))}
          </div>

           {/* Empty results message */}
           {results.length === 0 && (
            <div className="flex items-center justify-center h-48 border-2 border-dashed border-gray-300 rounded-xl bg-gray-50 dark:bg-gray-800 dark:border-gray-700">
                 <p className="text-base text-muted-foreground p-4">
                    No matching results found in the media library for this query.
                </p>
            </div>
          )}
        </div>
        
        {/* Debug Panel */}
        {rawResponse && (
            <Accordion type="single" collapsible className="w-full">
                <AccordionItem value="item-1">
                    <AccordionTrigger>
                        <div className="flex items-center gap-2 text-gray-800 dark:text-gray-100 hover:no-underline">
                           <Beaker className="h-5 w-5 text-red-500" />
                           <span className="font-semibold">Debug Panel (Raw API Response)</span>
                        </div>
                    </AccordionTrigger>
                    <AccordionContent>
                       <pre className="p-4 bg-gray-100 dark:bg-gray-900 rounded-md text-xs overflow-auto text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-700">
                         {JSON.stringify(rawResponse, null, 2)}
                       </pre>
                    </AccordionContent>
                </AccordionItem>
            </Accordion>
        )}
      </div>
    </div>
  );
}