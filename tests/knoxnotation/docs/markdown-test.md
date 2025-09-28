Line 1
Line 2

Line 4 after a blank line.


Line 7 after two blank lines.

# Links and Images in Markdown
- Link syntax: `[text](URL)`.
- Image syntax: `![text](URL)`. Note that the difference is that the image syntax starts with an exclamation mark.

# Automatic Links in Markdown
Markdown supports a shortcut style for creating “automatic” links for URLs and email addresses: simply surround the URL or email address with angle brackets. What this means is that if you want to show the actual text of a URL or email address, and also have it be a clickable link, you can do this:
```Markdown
<http://example.com/>
```

Markdown will turn this into:
```HTML
<a href="http://example.com/">http://example.com/</a>
```

Source: <https://stackoverflow.com/a/24888940/15416680>.

# Obsidian Types of Callouts

## Syntax

```markdown
>[!callout] Title
> Content
```

## Types

>[!note] note
> The first one I already showed you, this is a note. I put this within code blocks just to show you the syntax. And then this is what it looks like. Basically, this is the standard format of callouts, you just change whatever’s here. And then you always put the title outside of the brackets, and then the content of the note below it. So this is what a note looks like. That’s probably the most common.

>[!abstract] abstract, summary, tldr
>Now, all of these are the same, so like this is a TLDR, so I can actually edit it here as well. So here in this case, I was using TLDR, but if I do abstract, it’s going to look, actually, it looks a little bit different now that I think about it I thought it was going to look the same, but it’s also dependent on the theme that you’re using.
>
>Yeah, so these three are actually different, even though they’re semantically the same. Well, that’s interesting. I just literally found that out right now as well.

>[!info] info, todo
> And there’s info and todo. So this I believe is the todo. And if I go to info, it looks slightly different, just has a little eye here.
> 
> This is what I use for descriptions. What we call it in TTRPG is what we call box text, when players enter a new scene and there’s a part that you read out word for word, rather than improvising it. This is what I use for it.

>[!tip] tip, hint, important
>Then you have tips, hint, tip, hint, or important. This one is a tip.
>
>Let’s see what important looks like. All right. Yeah, all right. So there’s some highlighting going on there as well, and it’s marked by an asterisk.

>[!success] success, check, done
>
>There’s success, check, done. I particularly like, I think it was done. It’s kind of like the todo had a checkbox. This one actually has the check.

>[!questions] questions, help, faq
>There’s questions, help, or faq.

>[!warning] warning, caution, attention
> There’s warning, caution, or attention, which is what I use for errors or gotchas when you’re programming or something things that you might fall into that I want to call out, because I did fall into it.

>[!fail] fail, failure, missing
>And there’s also fail, failure, and missing. So this is all bad stuff, essentially.

>[!danger] danger, error
There’s danger, error. It looks like this with a little lightning symbol.

>[!bug] bug
>There’s bug, which I use quite a bit when I’m reporting bugs or documenting bugs, anyway. This example, which kind of looks like abstract, actually.

>[!quote] quote, cite
Quote, and cite, which is kind of a blockquote, except a little bit fancier.

Source: [Obsidian Callouts | Nicole van der Hoeven](https://nicolevanderhoeven.com/blog/20220330-new-in-obsidian-obsidian-callouts/).