
'use client';

import { useState, type ReactNode } from 'react';
import { z } from 'zod';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
  DialogClose,
} from '@/components/ui/dialog';
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import type { Movie, Short } from '@/lib/types';
import { Loader2, Wand2 } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { suggestShort, type SuggestShortInput } from '@/ai/flows/suggest-short';
import { Separator } from './ui/separator';

const shortSchema = z.object({
  title: z.string().min(1, 'Title is required.'),
  description: z.string().min(1, 'Description is required.'),
  startTime: z.string().min(1, 'Start time is required.').regex(/^\d{1,2}:\d{2}$|^\d{1,2}:\d{2}:\d{2}$/, 'Invalid time format (use MM:SS or HH:MM:SS).'),
  endTime: z.string().min(1, 'End time is required.').regex(/^\d{1,2}:\d{2}$|^\d{1,2}:\d{2}:\d{2}$/, 'Invalid time format (use MM:SS or HH:MM:SS).'),
  objective: z.string().optional(),
});

type ShortFormValues = z.infer<typeof shortSchema>;

interface AddShortWizardProps {
  children: ReactNode;
  movie: Movie;
  onAddShort: (newShort: Short) => void;
}

export function AddShortWizard({ children, movie, onAddShort }: AddShortWizardProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isSuggesting, setIsSuggesting] = useState(false);
  const { toast } = useToast();

  const form = useForm<ShortFormValues>({
    resolver: zodResolver(shortSchema),
    defaultValues: {
      title: '',
      description: '',
      startTime: '',
      endTime: '',
      objective: 'Find a scene with a lot of tension or conflict.',
    },
  });

  const handleGenerate = async () => {
    // This is deprecated as shorts are now auto-generated
    toast({
        variant: 'default',
        title: 'Feature Not Available',
        description: 'Short suggestions are now automatically generated from media analysis.',
    });
    return;
  };

  const onSubmit = (values: ShortFormValues) => {
    const videoUrl = movie.public_url;

    const newShort: Short = {
      id: `${movie.id}-short-${Date.now()}`,
      title: values.title,
      description: values.description,
      startTime: values.startTime,
      endTime: values.endTime,
      videoUrl: videoUrl,
      thumbnailUrl: 'https://placehold.co/400x225.png', // Placeholder thumbnail
      categories: ['New'],
    };
    onAddShort(newShort);
    setIsOpen(false);
    form.reset();
  };

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>{children}</DialogTrigger>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Add New Short to {movie.file_name}</DialogTitle>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
             <div className="space-y-2 rounded-lg border p-4">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <Wand2 className="h-5 w-5 text-primary" />
                AI Suggestion (Not Available)
              </h3>
               <FormField
                  control={form.control}
                  name="objective"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Objective</FormLabel>
                      <FormControl>
                         <Textarea placeholder="e.g., Find an action-packed scene" {...field} disabled />
                      </FormControl>
                      <FormDescription>
                        Shorts are now generated automatically based on the video analysis. Manual suggestions are disabled.
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              <Button type="button" onClick={handleGenerate} disabled>
                  <Wand2 className="mr-2 h-4 w-4" />
                  Suggest with AI
              </Button>
            </div>

            <div className="flex items-center space-x-2">
                <Separator className="flex-1" />
                <span className="text-xs text-muted-foreground">OR</span>
                <Separator className="flex-1" />
            </div>

            <p className="text-center text-sm text-muted-foreground">
              Manually fill out the details for the new short.
            </p>

            <FormField
              control={form.control}
              name="title"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Title</FormLabel>
                  <FormControl>
                    <Input placeholder="Enter a catchy title" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Description</FormLabel>
                  <FormControl>
                    <Textarea placeholder="Describe the scene" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
             <div className="grid grid-cols-2 gap-4">
                <FormField
                control={form.control}
                name="startTime"
                render={({ field }) => (
                    <FormItem>
                    <FormLabel>Start Time</FormLabel>
                    <FormControl>
                        <Input placeholder="MM:SS" {...field} />
                    </FormControl>
                    <FormMessage />
                    </FormItem>
                )}
                />
                <FormField
                control={form.control}
                name="endTime"
                render={({ field }) => (
                    <FormItem>
                    <FormLabel>End Time</FormLabel>
                    <FormControl>
                        <Input placeholder="MM:SS" {...field} />
                    </FormControl>
                    <FormMessage />
                    </FormItem>
                )}
                />
            </div>
            <DialogFooter>
              <DialogClose asChild>
                <Button type="button" variant="ghost">Cancel</Button>
              </DialogClose>
              <Button type="submit">Create Short</Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
