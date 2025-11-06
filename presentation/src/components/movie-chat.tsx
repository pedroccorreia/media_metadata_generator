
'use client';

import { useState, useEffect, useRef } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { movieChat } from '@/ai/flows/movie-chat';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Bot, Loader2, User } from 'lucide-react';
import { Form, FormControl, FormField, FormItem, FormMessage } from '@/components/ui/form';
import { ScrollArea } from './ui/scroll-area';

const chatSchema = z.object({
  query: z.string().min(1, 'Please enter a message.'),
});

type ChatFormValues = z.infer<typeof chatSchema>;

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

interface MovieChatProps {
    initialQuery?: string;
}

export function MovieChat({ initialQuery }: MovieChatProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const hasSentInitialQuery = useRef(false);

  const form = useForm<ChatFormValues>({
    resolver: zodResolver(chatSchema),
    defaultValues: {
      query: '',
    },
  });

  const onSubmit = async (query: string) => {
    setIsLoading(true);
    const userMessage: Message = { role: 'user', content: query };
    const newMessages: Message[] = [...messages, userMessage];
    setMessages(newMessages);
    form.reset();

    try {
      // Pass the new message history to the flow
      const response = await movieChat({ query: query, history: newMessages });
      const assistantMessage: Message = { role: 'assistant', content: response.answer };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error calling movieChat flow:', error);
      const errorMessage: Message = {
        role: 'assistant',
        content: 'Sorry, I had trouble finding an answer. Please try again.',
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFormSubmit = (values: ChatFormValues) => {
    onSubmit(values.query);
  };
  
  useEffect(() => {
    if (initialQuery && !hasSentInitialQuery.current) {
        hasSentInitialQuery.current = true;
        onSubmit(initialQuery);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialQuery]);

  return (
    <div className="space-y-4">
      <ScrollArea className="h-64 pr-4">
        <div className="space-y-4">
          {messages.map((message, index) => (
            <div
              key={index}
              className={`flex gap-3 ${
                message.role === 'user' ? 'justify-end' : 'justify-start'
              }`}
            >
              {message.role === 'assistant' && (
                <div className="bg-primary text-primary-foreground rounded-full h-8 w-8 flex items-center justify-center flex-shrink-0">
                  <Bot size={20} />
                </div>
              )}
              <div
                className={`rounded-lg px-4 py-2 max-w-sm ${
                  message.role === 'user'
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-secondary'
                }`}
              >
                <p className="text-sm">{message.content}</p>
              </div>
               {message.role === 'user' && (
                 <div className="bg-muted text-muted-foreground rounded-full h-8 w-8 flex items-center justify-center flex-shrink-0">
                  <User size={20} />
                </div>
              )}
            </div>
          ))}
           {isLoading && messages[messages.length -1]?.role === 'user' && (
            <div className="flex gap-3 justify-start">
              <div className="bg-primary text-primary-foreground rounded-full h-8 w-8 flex items-center justify-center flex-shrink-0">
                  <Bot size={20} />
              </div>
               <div className="rounded-lg px-4 py-2 bg-secondary flex items-center">
                    <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                </div>
            </div>
            )}
        </div>
      </ScrollArea>
      <Form {...form}>
        <form onSubmit={form.handleSubmit(handleFormSubmit)} className="flex gap-2">
          <FormField
            control={form.control}
            name="query"
            render={({ field }) => (
              <FormItem className="flex-grow">
                <FormControl>
                  <Input placeholder="Ask about this movie..." {...field} disabled={isLoading} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <Button type="submit" disabled={isLoading}>
            {isLoading ? <Loader2 className="h-5 w-5 animate-spin" /> : 'Send'}
          </Button>
        </form>
      </Form>
    </div>
  );
}
