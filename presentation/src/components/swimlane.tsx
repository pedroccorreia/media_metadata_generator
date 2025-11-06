
import {
  Carousel,
  CarouselContent,
  CarouselItem,
  CarouselNext,
  CarouselPrevious,
} from '@/components/ui/carousel';
import { ShortCard } from '@/components/short-card';
import type { ShortWithMovieInfo } from '@/lib/types';
import { Card, CardContent } from '@/components/ui/card';

interface SwimlaneProps {
  title: string;
  shorts: ShortWithMovieInfo[];
}

export function Swimlane({ title, shorts }: SwimlaneProps) {
  return (
    <section>
      <h2 className="text-2xl font-bold tracking-tight mb-4">{title}</h2>
      {shorts && shorts.length > 0 ? (
        <Carousel
          opts={{
            align: 'start',
            loop: shorts.length > 1, // Only loop if there's more than one item
          }}
          className="w-full"
        >
          <CarouselContent>
            {shorts.map((short) => (
              <CarouselItem key={short.id} className="md:basis-1/2 lg:basis-1/3 xl:basis-1/4">
                <div className="p-1">
                  <ShortCard short={short} />
                </div>
              </CarouselItem>
            ))}
          </CarouselContent>
          <CarouselPrevious className="hidden sm:flex" />
          <CarouselNext className="hidden sm:flex" />
        </Carousel>
      ) : (
        <Card className="flex items-center justify-center h-48 border-2 border-dashed">
            <CardContent className="p-6 pt-6">
                 <p className="text-muted-foreground">Coming soon!</p>
            </CardContent>
        </Card>
      )}
    </section>
  );
}
