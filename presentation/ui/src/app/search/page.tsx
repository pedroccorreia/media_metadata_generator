
import { searchVAIS } from '@/lib/vais';
import Link from 'next/link';
import Image from 'next/image';
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

interface SearchPageProps {
  searchParams: {
    q?: string | string[];
  };
}

export default async function SearchPage({ searchParams }: SearchPageProps) {
  const query = Array.isArray(searchParams.q) ? searchParams.q[0] : searchParams.q;

  if (!query) {
    return (
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="text-center">
          <h1 className="text-4xl font-bold">Search</h1>
          <p className="mt-4 text-muted-foreground">
            Please enter a search query to begin.
          </p>
        </div>
      </div>
    );
  }

  const { summary, results, rawResponse } = await searchVAIS(query);

  return (
    <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="mb-8">
        <h1 className="text-3xl font-extrabold tracking-tight">
          Search Results for "{query}"
        </h1>
      </div>

       <div className="space-y-8">
         <Card>
            <CardHeader>
              <CardTitle>AI Summary</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground">{summary}</p>
            </CardContent>
          </Card>
        
        <div>
          <h2 className="text-2xl font-bold tracking-tight mb-4">
            References
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {results.map((result, index) => (
                <Card key={index} className="flex flex-col overflow-hidden">
                    {result.posterUrl && (
                        <div className="relative aspect-video w-full">
                            <Image 
                                src={result.posterUrl}
                                alt={`Poster for ${result.title}`}
                                fill
                                data-ai-hint="movie poster"
                                className="object-cover"
                            />
                        </div>
                    )}
                    <CardHeader>
                        <CardTitle className="text-lg">
                             <Link
                                href={result.url}
                                className="group flex items-start gap-2 text-primary hover:underline transition-colors"
                                >
                                <LinkIcon className="h-4 w-4 mt-1 flex-shrink-0" />
                                <span className="truncate">
                                    {result.title}
                                </span>
                            </Link>
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="flex-grow">
                      {result.snippet && (
                        <div className="flex gap-3 items-start text-sm text-muted-foreground">
                            <FileText className="h-4 w-4 mt-0.5 flex-shrink-0"/>
                            <p className="italic" dangerouslySetInnerHTML={{ __html: result.snippet }} />
                        </div>
                      )}
                    </CardContent>
                </Card>
            ))}
          </div>
           {results.length === 0 && (
            <div className="flex items-center justify-center h-48 border-2 border-dashed rounded-lg">
                 <p className="text-sm text-muted-foreground">
                    No results found in the media library for this query.
                </p>
            </div>
          )}
        </div>
        {rawResponse && (
            <Accordion type="single" collapsible className="w-full">
                <AccordionItem value="item-1">
                    <AccordionTrigger>
                        <div className="flex items-center gap-2">
                           <Beaker className="h-5 w-5" />
                           <span className="font-semibold">Debug Panel</span>
                        </div>
                    </AccordionTrigger>
                    <AccordionContent>
                       <pre className="p-4 bg-muted rounded-md text-xs overflow-auto">
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
