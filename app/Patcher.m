#import <Cocoa/Cocoa.h>

@interface Patcher : NSObject <NSApplicationDelegate, NSWindowDelegate>
@property NSWindow *window;
@property NSTextField *pathLabel, *statusLabel, *versionLabel;
@property NSProgressIndicator *progress;
@property NSButton *chooseButton, *installButton, *restoreButton, *launchButton;
@property NSURL *selected;
@property NSTask *job;
@property NSMutableData *lines;
@property NSDictionary *received;
@property NSString *operation;
@property BOOL supported, restorable;
@end

@implementation Patcher
+ (NSString *)python {
    for (NSString *p in @[@"/Library/Frameworks/Python.framework/Versions/3.15/bin/python3", @"/opt/homebrew/bin/python3", @"/usr/local/bin/python3", @"/usr/bin/python3"])
        if ([[NSFileManager defaultManager] isExecutableFileAtPath:p]) return p;
    return nil;
}
+ (NSURL *)backend {
    return [[[NSBundle mainBundle] resourceURL] URLByAppendingPathComponent:@"project/tools/gui_backend.py"];
}
- (NSTextField *)label:(NSString *)text size:(CGFloat)size secondary:(BOOL)secondary {
    NSTextField *v=[NSTextField wrappingLabelWithString:text];
    v.font=[NSFont systemFontOfSize:size];
    if (secondary) v.textColor=NSColor.secondaryLabelColor;
    return v;
}
- (NSButton *)button:(NSString *)title action:(SEL)action {
    return [NSButton buttonWithTitle:title target:self action:action];
}
- (void)applicationDidFinishLaunching:(NSNotification *)note {
    [NSApp setActivationPolicy:NSApplicationActivationPolicyRegular];
    NSMenu *menu=[NSMenu new], *appMenu=[NSMenu new]; NSMenuItem *item=[NSMenuItem new];
    [appMenu addItemWithTitle:@"О ChatGPT Themes" action:@selector(orderFrontStandardAboutPanel:) keyEquivalent:@""];
    [appMenu addItem:NSMenuItem.separatorItem];
    [appMenu addItemWithTitle:@"Завершить ChatGPT Themes" action:@selector(terminate:) keyEquivalent:@"q"];
    item.submenu=appMenu; [menu addItem:item]; NSApp.mainMenu=menu;
    self.window=[[NSWindow alloc] initWithContentRect:NSMakeRect(0,0,620,500)
        styleMask:NSWindowStyleMaskTitled|NSWindowStyleMaskClosable|NSWindowStyleMaskMiniaturizable
        backing:NSBackingStoreBuffered defer:NO];
    self.window.title=@"ChatGPT Themes Patcher"; self.window.delegate=self;
    self.window.releasedWhenClosed=NO;
    self.window.appearance=[NSAppearance appearanceNamed:NSAppearanceNameDarkAqua];
    NSView *content=[NSView new]; self.window.contentView=content;
    NSStackView *stack=[NSStackView new]; stack.orientation=NSUserInterfaceLayoutOrientationVertical;
    stack.alignment=NSLayoutAttributeLeading; stack.spacing=18;
    stack.translatesAutoresizingMaskIntoConstraints=NO; [content addSubview:stack];
    [NSLayoutConstraint activateConstraints:@[[stack.leadingAnchor constraintEqualToAnchor:content.leadingAnchor constant:28],
        [stack.trailingAnchor constraintEqualToAnchor:content.trailingAnchor constant:-28],
        [stack.topAnchor constraintEqualToAnchor:content.topAnchor constant:26]]];
    NSTextField *title=[self label:@"ChatGPT Themes" size:28 secondary:NO];
    title.font=[NSFont systemFontOfSize:28 weight:NSFontWeightBold]; [stack addArrangedSubview:title];
    [stack addArrangedSubview:[self label:@"Темы в привычном приложении. Без Терминала." size:14 secondary:YES]];
    [stack addArrangedSubview:[self label:@"ПРИЛОЖЕНИЕ" size:11 secondary:YES]];
    self.selected=[NSURL fileURLWithPath:@"/Applications/ChatGPT.app"];
    self.pathLabel=[NSTextField labelWithString:self.selected.path];
    self.pathLabel.lineBreakMode=NSLineBreakByTruncatingMiddle;
    [self.pathLabel setContentCompressionResistancePriority:NSLayoutPriorityDefaultLow forOrientation:NSLayoutConstraintOrientationHorizontal];
    self.chooseButton=[self button:@"Выбрать…" action:@selector(pick:)];
    NSStackView *row=[NSStackView stackViewWithViews:@[self.pathLabel,self.chooseButton]];
    row.orientation=NSUserInterfaceLayoutOrientationHorizontal; row.spacing=12; [stack addArrangedSubview:row];
    [row.widthAnchor constraintEqualToAnchor:stack.widthAnchor].active=YES;
    self.versionLabel=[self label:@"" size:12 secondary:YES]; [stack addArrangedSubview:self.versionLabel];
    NSBox *divider=[NSBox new]; divider.boxType=NSBoxSeparator; [stack addArrangedSubview:divider];
    [divider.widthAnchor constraintEqualToAnchor:stack.widthAnchor].active=YES;
    self.statusLabel=[self label:@"Проверяю приложение…" size:14 secondary:NO];
    self.statusLabel.maximumNumberOfLines=4; [stack addArrangedSubview:self.statusLabel];
    [self.statusLabel.widthAnchor constraintEqualToAnchor:stack.widthAnchor].active=YES;
    self.progress=[NSProgressIndicator new]; self.progress.style=NSProgressIndicatorStyleBar;
    self.progress.indeterminate=NO; self.progress.maxValue=100; [stack addArrangedSubview:self.progress];
    [self.progress.widthAnchor constraintEqualToAnchor:stack.widthAnchor].active=YES;
    self.installButton=[self button:@"Установить / Обновить" action:@selector(apply:)];
    self.installButton.bezelColor=NSColor.systemPurpleColor;
    self.restoreButton=[self button:@"Откатить" action:@selector(rollback:)];
    self.launchButton=[self button:@"Открыть ChatGPT" action:@selector(openApp:)];
    NSStackView *buttons=[NSStackView stackViewWithViews:@[self.installButton,self.restoreButton,self.launchButton]];
    buttons.orientation=NSUserInterfaceLayoutOrientationHorizontal; buttons.spacing=10;
    [stack addArrangedSubview:buttons];
    NSTextField *foot=[self label:@"Сохраняется версия до первой установки этим патчером. После локальной переподписи macOS может повторно запросить доступ к Keychain. Обновление ChatGPT может убрать патч." size:11 secondary:YES];
    [stack addArrangedSubview:foot]; [foot.widthAnchor constraintEqualToAnchor:stack.widthAnchor].active=YES;
    [self.window center]; [self.window makeKeyAndOrderFront:nil]; [NSApp activateIgnoringOtherApps:YES];
    [self execute:@"inspect"];
}
- (void)pick:(id)sender {
    NSOpenPanel *panel=[NSOpenPanel openPanel]; panel.canChooseFiles=YES; panel.canChooseDirectories=NO;
    panel.allowedFileTypes=@[@"app"]; panel.allowsMultipleSelection=NO;
    panel.directoryURL=[self.selected URLByDeletingLastPathComponent]; panel.prompt=@"Выбрать ChatGPT";
    [panel beginSheetModalForWindow:self.window completionHandler:^(NSModalResponse result){
        if (result==NSModalResponseOK && panel.URL) {
            self.selected=panel.URL; self.pathLabel.stringValue=panel.URL.path;
            [self execute:@"inspect"];
        }
    }];
}
- (void)apply:(id)sender { [self execute:@"apply"]; }
- (void)rollback:(id)sender {
    NSAlert *alert=[NSAlert new]; alert.messageText=@"Вернуть версию до патчера?";
    alert.informativeText=@"Будет восстановлена сохранённая копия приложения. Аккаунт и чаты не переносятся и не удаляются. ChatGPT должен быть закрыт.";
    [alert addButtonWithTitle:@"Восстановить"]; [alert addButtonWithTitle:@"Отмена"];
    [alert beginSheetModalForWindow:self.window completionHandler:^(NSModalResponse r){
        if(r==NSAlertFirstButtonReturn) [self execute:@"restore"];
    }];
}
- (void)openApp:(id)sender { [[NSWorkspace sharedWorkspace] openURL:self.selected]; }
- (void)buttons {
    BOOL idle=self.job==nil;
    self.chooseButton.enabled=idle; self.installButton.enabled=idle&&self.supported;
    self.restoreButton.enabled=idle&&self.restorable; self.launchButton.enabled=idle;
}
- (void)execute:(NSString *)action {
    if(self.job) return;
    NSString *python=[Patcher python]; NSURL *backend=[Patcher backend];
    if(!python || ![[NSFileManager defaultManager] fileExistsAtPath:backend.path]) {
        [self showError:@"Нужен установленный Python 3 и полный комплект файлов патчера."]; return;
    }
    self.operation=action; self.received=nil; self.lines=[NSMutableData new];
    if([action isEqual:@"inspect"]) { self.supported=NO; self.restorable=NO; self.versionLabel.stringValue=@""; }
    self.statusLabel.stringValue=[action isEqual:@"inspect"]?@"Проверяю приложение…":@"Подготавливаю операцию…";
    self.progress.doubleValue=0;
    NSTask *task=[NSTask new]; NSPipe *out=[NSPipe pipe], *err=[NSPipe pipe];
    task.executableURL=[NSURL fileURLWithPath:python];
    task.arguments=@[@"-u",backend.path,action,@"--app",self.selected.path];
    task.standardOutput=out; task.standardError=err; self.job=task; [self buttons];
    NSError *error=nil;
    if(![task launchAndReturnError:&error]) {
        self.job=nil; [self buttons]; [self showError:error.localizedDescription]; return;
    }
    dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INITIATED,0), ^{
        while(YES) {
            NSData *data=[out.fileHandleForReading availableData];
            if(data.length==0) break;
            dispatch_async(dispatch_get_main_queue(), ^{ [self consume:data]; });
        }
        [task waitUntilExit]; int code=task.terminationStatus;
        dispatch_async(dispatch_get_main_queue(), ^{ [self finished:code]; });
    });
    dispatch_async(dispatch_get_global_queue(QOS_CLASS_UTILITY,0), ^{ [err.fileHandleForReading readDataToEndOfFile]; });
}
- (void)consume:(NSData *)data {
    [self.lines appendData:data]; const unsigned char nl=10;
    while(YES) {
        NSRange r=[self.lines rangeOfData:[NSData dataWithBytes:&nl length:1] options:0 range:NSMakeRange(0,self.lines.length)];
        if(r.location==NSNotFound) break;
        NSData *line=[self.lines subdataWithRange:NSMakeRange(0,r.location)];
        [self.lines replaceBytesInRange:NSMakeRange(0,r.location+1) withBytes:NULL length:0];
        id value=[NSJSONSerialization JSONObjectWithData:line options:0 error:nil];
        if(![value isKindOfClass:NSDictionary.class]) continue;
        if([value[@"event"] isEqual:@"progress"]) {
            self.statusLabel.stringValue=value[@"message"]?:@"";
            self.progress.doubleValue=[value[@"percent"] doubleValue];
        } else self.received=value;
    }
}
- (void)finished:(int)code {
    self.job=nil;
    if(code!=0 || [self.received[@"event"] isEqual:@"error"]) {
        self.statusLabel.stringValue=@"Операция остановлена"; [self buttons];
        [self showError:self.received[@"message"]?:@"Нет результата. Проверьте наличие Python 3 и выбранного приложения."]; return;
    }
    if([self.operation isEqual:@"inspect"]) {
        self.supported=[self.received[@"supported"] boolValue]; self.restorable=[self.received[@"canRestore"] boolValue];
        self.versionLabel.stringValue=[NSString stringWithFormat:@"ChatGPT %@ · сборка %@",self.received[@"version"]?:@"?",self.received[@"build"]?:@"?"];
        self.statusLabel.stringValue=self.supported?@"Готово к установке. Сначала полностью выйдите из ChatGPT через ⌘Q.":@"Эта версия пока не поддерживается. Доступен откат, если есть резервная копия.";
    } else {
        self.progress.doubleValue=100; self.restorable=YES;
        self.statusLabel.stringValue=[self.received[@"unchanged"] boolValue]?@"Менеджер уже актуален. Переподпись не требуется.":([self.operation isEqual:@"restore"]?@"Предыдущая версия восстановлена. Можно открыть ChatGPT.":@"Менеджер установлен. Откройте ChatGPT → меню аккаунта → Темы.");
    }
    [self buttons];
}
- (void)showError:(NSString *)message {
    NSAlert *alert=[NSAlert new]; alert.alertStyle=NSAlertStyleWarning;
    alert.messageText=@"Не удалось завершить операцию"; alert.informativeText=message;
    [alert addButtonWithTitle:@"Понятно"]; [alert beginSheetModalForWindow:self.window completionHandler:nil];
}
- (BOOL)windowShouldClose:(NSWindow *)sender { if(self.job) {NSBeep();return NO;} return YES; }
- (NSApplicationTerminateReply)applicationShouldTerminate:(NSApplication *)sender {return self.job?NSTerminateCancel:NSTerminateNow;}
- (BOOL)applicationShouldTerminateAfterLastWindowClosed:(NSApplication *)sender {return YES;}
@end

static Patcher *keepAlive;
int main(int argc, const char *argv[]) {
    @autoreleasepool {
        if([NSProcessInfo.processInfo.arguments containsObject:@"--self-test"]) {
            NSString *python=[Patcher python];NSURL *backend=[Patcher backend];
            if(!python || ![[NSFileManager defaultManager] fileExistsAtPath:backend.path]) return 1;
            printf("Runtime resources found; Python: %s\n",python.UTF8String);return 0;
        }
        [NSApplication sharedApplication];keepAlive=[Patcher new];NSApp.delegate=keepAlive;[NSApp run];
    }
    return 0;
}
