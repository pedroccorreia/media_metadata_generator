export function Footer() {
  return (
    <footer className="border-t">
      <div className="container flex-col gap-4 sm:flex-row py-6 text-center sm:text-left flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          &copy; {new Date().getFullYear()} CineShorts. All rights reserved.
        </p>
        <div className="flex items-center gap-4">
            <p className="text-sm text-muted-foreground">Privacy Policy</p>
            <p className="text-sm text-muted-foreground">Terms of Service</p>
        </div>
      </div>
    </footer>
  );
}
