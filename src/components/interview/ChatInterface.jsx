// src/components/interview/ChatInterface.jsx
import { useState, useEffect, useRef } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Send, User, Bot, Loader2, Sparkles, Trophy, Clock, Mic, MicOff } from 'lucide-react';
import {
    addChatMessage,
    updateCandidateInfo,
    addQuestion,
    updateQuestion,
    setCurrentQuestionIndex,
    updateTotalScore,
    setFinalSummary,
    updateInterviewStatus,
    setProcessing,
} from '@/store/slices/candidateSlice';
import { InterviewStatus, QuestionDifficulty } from '@/store/types';
//import { OpenAIService } from '@/services/openai.service';
import { GeminiService } from '@/services/gemini.service';
import { getMissingFields, validateEmail, validatePhone, validateName } from '@/utils/validators';
import { generateId, getQuestionSequence } from '@/utils/helpers';

export const ChatInterface = () => {
    const dispatch = useDispatch();
    const { currentCandidateId, candidates, isProcessing } = useSelector(
        (state) => state.interview
    );

    const candidate = currentCandidateId ? candidates[currentCandidateId] : null;
    const [inputValue, setInputValue] = useState('');
    const scrollRef = useRef(null);
    const [missingFields, setMissingFields] = useState([]);
    const [collectingField, setCollectingField] = useState(null);
    const askedOnce = useRef(false);
    const [isListening, setIsListening] = useState(false);
    const generatingQuestion = useRef(false);

    // ✅ Auto-scroll to bottom whenever chat history updates
    useEffect(() => {
        if (scrollRef.current) {
            const scrollElement = scrollRef.current.querySelector('[data-radix-scroll-area-viewport]');
            if (scrollElement) {
                scrollElement.scrollTop = scrollElement.scrollHeight;
            }
        }
    }, [candidate?.chatHistory]);

    // ✅ Also scroll when processing state changes (for "Thinking..." message)
    useEffect(() => {
        if (scrollRef.current && isProcessing) {
            setTimeout(() => {
                const scrollElement = scrollRef.current?.querySelector('[data-radix-scroll-area-viewport]');
                if (scrollElement) {
                    scrollElement.scrollTop = scrollElement.scrollHeight;
                }
            }, 100);
        }
    }, [isProcessing]);

    useEffect(() => {
        // ✅ Reset processing state when component mounts or candidate changes
        if (candidate && candidate.status === InterviewStatus.COLLECTING_INFO) {
            dispatch(setProcessing(false));

            const missing = getMissingFields(candidate.info);
            setMissingFields(missing);

            if (
                missing.length > 0 &&
                candidate.chatHistory.length === 0 &&
                collectingField === null &&
                !askedOnce.current
            ) {
                askedOnce.current = true;
                setCollectingField(missing[0]);
                addSystemMessage(`Please provide your ${missing[0]}.`);
            } else if (missing.length === 0 && !generatingQuestion.current) {
                startInterview();
            }
        }
    }, [candidate?.status, collectingField]);

    const addSystemMessage = (content) => {
        if (!currentCandidateId) return;
        const message = {
            id: generateId(),
            role: 'assistant',
            content,
            timestamp: Date.now(),
        };
        dispatch(addChatMessage({ id: currentCandidateId, message }));
    };

    const addUserMessage = (content) => {
        if (!currentCandidateId) return;
        const message = {
            id: generateId(),
            role: 'user',
            content,
            timestamp: Date.now(),
        };
        dispatch(addChatMessage({ id: currentCandidateId, message }));
    };

    const handleCollectInfo = async (value) => {
        if (!currentCandidateId || !collectingField) return;

        addUserMessage(value);
        setInputValue(''); // Clear the input

        let isValid = false;
        let errorMessage = '';

        if (collectingField === 'name') {
            isValid = validateName(value);
            errorMessage = 'Please provide a valid name (only letters and spaces).';
        } else if (collectingField === 'email') {
            isValid = validateEmail(value);
            errorMessage = 'Please provide a valid email address.';
        } else if (collectingField === 'phone') {
            isValid = validatePhone(value);
            errorMessage = 'Please provide a valid phone number (at least 10 digits).';
        }

        if (!isValid) {
            addSystemMessage(errorMessage);
            return;
        }

        dispatch(updateCandidateInfo({
            id: currentCandidateId,
            info: { [collectingField]: value },
        }));

        const updatedMissing = missingFields.filter(f => f !== collectingField);
        setMissingFields(updatedMissing);

        if (updatedMissing.length > 0) {
            setCollectingField(updatedMissing[0]);
            addSystemMessage(`Great! Now, please provide your ${updatedMissing[0]}.`);
        } else {
            setCollectingField(null);
            dispatch(setProcessing(false)); // ✅ Add this line
            addSystemMessage(
                `Great! You're all set. We'll start the interview session now. You'll answer six questions: 2 Easy, 2 Medium, and 2 Hard.`
            );

            setTimeout(() => {
                startInterview();
            }, 1500);
        }
    };

    const startInterview = async () => {
        if (!currentCandidateId || !candidate) return;

        // guard to prevent multiple calls
        if (candidate.status === InterviewStatus.IN_PROGRESS) return;
        dispatch(updateInterviewStatus({ id: currentCandidateId, status: InterviewStatus.IN_PROGRESS }));
        await generateNextQuestion();
    };

    const generateNextQuestion = async () => {
        if (!currentCandidateId || !candidate) return;
        if (isProcessing || generatingQuestion.current) return; // ✅ Check ref

        generatingQuestion.current = true; // ✅ Set flag

        const questionSequence = getQuestionSequence();
        const nextIndex = candidate.questions.length;

        if (nextIndex >= 6) {
            generatingQuestion.current = false; // ✅ Reset flag
            await completeInterview();
            return;
        }

        dispatch(setProcessing(true));

        try {
            const difficulty = questionSequence[nextIndex];
            const previousQuestions = candidate.questions.map(q => q.text);
            const questionText = await GeminiService.generateQuestion(difficulty, previousQuestions);

            const question = {
                id: generateId(),
                text: questionText,
                difficulty,
                timestamp: Date.now(),
            };

            dispatch(addQuestion({ id: currentCandidateId, question }));
            dispatch(setCurrentQuestionIndex({ id: currentCandidateId, index: nextIndex }));

            addSystemMessage(`**Question ${nextIndex + 1}/6** (${difficulty})\n\n${questionText}`);

        } catch (error) {
            addSystemMessage(`Error generating question: ${error.message}. Please refresh and try again.`);
        } finally {
            dispatch(setProcessing(false));
            generatingQuestion.current = false; // ✅ Reset flag in finally
        }
    };

    const handleSubmitAnswer = async () => {
        if (!currentCandidateId || !candidate || !inputValue.trim()) return;
        if (isProcessing) return;
        const currentQuestionIndex = candidate.currentQuestionIndex;
        const currentQuestion = candidate.questions[currentQuestionIndex];
        if (!currentQuestion) return;

        const answerToSubmit = inputValue.trim();
        addUserMessage(answerToSubmit);
        setInputValue(''); // Clear input immediately

        dispatch(setProcessing(true));

        try {
            const { score, judgement } = await GeminiService.evaluateAnswer(
                currentQuestion.text,
                answerToSubmit,
                currentQuestion.difficulty
            );

            dispatch(updateQuestion({
                id: currentCandidateId,
                questionIndex: currentQuestionIndex,
                updates: {
                    answer: answerToSubmit,
                    score,
                    aiJudgement: judgement,
                },
            }));

            addSystemMessage(
                `**Evaluation:** ${judgement}\n\n**Score:** ${score}/${currentQuestion.difficulty === QuestionDifficulty.EASY
                    ? 10
                    : currentQuestion.difficulty === QuestionDifficulty.MEDIUM
                        ? 20
                        : 30
                }`
            );

            // ✅ Immediately move to next question (no delay)
            await generateNextQuestion();

        } catch (error) {
            addSystemMessage(`Error evaluating answer: ${error.message}`);
            dispatch(setProcessing(false));
        }
    };

    const completeInterview = async () => {
        if (!currentCandidateId || !candidate) return;
        dispatch(setProcessing(true));

        try {
            const totalScore = candidate.questions.reduce((sum, q) => sum + (q.score || 0), 0);
            dispatch(updateTotalScore({ id: currentCandidateId, score: totalScore }));

            const questionsForSummary = candidate.questions.map(q => ({
                question: q.text,
                answer: q.answer || 'No answer',
                score: q.score || 0,
                difficulty: q.difficulty,
            }));

            const summary = await GeminiService.generateFinalSummary(
                candidate.info.name || 'Candidate',
                questionsForSummary,
                totalScore
            );

            dispatch(setFinalSummary({ id: currentCandidateId, summary }));
            dispatch(updateInterviewStatus({ id: currentCandidateId, status: InterviewStatus.COMPLETED }));

            addSystemMessage(
                `🎉 **Session Complete!**\n\n**Final Score:** ${totalScore}/120\n\n**Summary:**\n${summary}\n\nThanks for your time!`
            );
        } catch (error) {
            addSystemMessage(`Error completing interview: ${error.message}`);
        } finally {
            dispatch(setProcessing(false));
        }
    };

    const handleSendMessage = () => {
        if (!inputValue.trim() || isProcessing) return;

        if (candidate?.status === InterviewStatus.COLLECTING_INFO) {
            handleCollectInfo(inputValue);
        } else if (candidate?.status === InterviewStatus.IN_PROGRESS) {
            handleSubmitAnswer();
        }
    };

    // 🎤 Speech recognition handler with continuous listening
    const recognitionRef = useRef(null);

    const handleVoiceInput = () => {
        if (!("webkitSpeechRecognition" in window)) {
            alert("Your browser does not support speech recognition. Try Chrome.");
            return;
        }

        // ✅ If already listening, stop it
        if (isListening && recognitionRef.current) {
            recognitionRef.current.stop();
            setIsListening(false);
            return;
        }

        // ✅ Start new recognition session
        const recognition = new window.webkitSpeechRecognition();
        recognition.continuous = true; // Keep listening continuously
        recognition.interimResults = true; // Show interim results as user speaks
        recognition.lang = "en-US";

        recognitionRef.current = recognition;

        recognition.onstart = () => setIsListening(true);

        recognition.onend = () => {
            setIsListening(false);
            recognitionRef.current = null;
        };

        recognition.onerror = (event) => {
            console.error("Speech recognition error:", event.error);
            setIsListening(false);
            recognitionRef.current = null;
        };

        recognition.onresult = (event) => {
            let interimTranscript = '';
            let finalTranscript = '';

            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    finalTranscript += transcript + ' ';
                } else {
                    interimTranscript += transcript;
                }
            }

            // ✅ Update input with final transcript, append to existing text
            if (finalTranscript) {
                setInputValue(prev => (prev + ' ' + finalTranscript).trim());
            }
        };

        recognition.start();
    };

    // ✅ Cleanup recognition on unmount
    useEffect(() => {
        return () => {
            if (recognitionRef.current) {
                recognitionRef.current.stop();
            }
        };
    }, []);

    if (!candidate) {
        return (
            <div className="flex items-center justify-center h-screen bg-gradient-to-br from-slate-50 to-emerald-50">
                <Loader2 className="h-8 w-8 animate-spin text-emerald-600" />
            </div>
        );
    }

    const currentQuestion = candidate.questions[candidate.currentQuestionIndex];

    const getDifficultyColor = (difficulty) => {
        switch (difficulty) {
            case 'Easy':
                return 'bg-green-100 text-green-700 border-green-200';
            case 'Medium':
                return 'bg-yellow-100 text-yellow-700 border-yellow-200';
            case 'Hard':
                return 'bg-red-100 text-red-700 border-red-200';
            default:
                return 'bg-slate-100 text-slate-700';
        }
    };

    return (
        <div className="flex flex-col h-screen bg-gradient-to-br from-slate-50 via-white to-emerald-50">
            {/* Header - Sticky at top */}
            <div className="sticky top-0 border-b bg-white/80 backdrop-blur-xl shadow-sm z-20 flex-shrink-0">
                <div className="max-w-5xl mx-auto px-4 sm:px-6 py-4">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-600 to-teal-600 flex items-center justify-center shadow-lg">
                                <Sparkles className="h-5 w-5 text-white" />
                            </div>
                            <div>
                                <h2 className="text-lg font-semibold text-slate-900">Interview Assistant</h2>
                                {candidate.info.name && (
                                    <p className="text-sm text-slate-600">Welcome, {candidate.info.name}</p>
                                )}
                            </div>
                        </div>
                        <div className="flex items-center gap-2">
                            {candidate.status === InterviewStatus.IN_PROGRESS && currentQuestion && (
                                <Badge
                                    variant="outline"
                                    className={`gap-1.5 px-3 py-1 border ${getDifficultyColor(
                                        currentQuestion.difficulty
                                    )}`}
                                >
                                    <Clock className="h-3 w-3" />
                                    Q{candidate.currentQuestionIndex + 1}/6
                                </Badge>
                            )}
                            {candidate.status === InterviewStatus.COMPLETED && (
                                <Badge
                                    variant="outline"
                                    className="gap-1.5 px-3 py-1 bg-green-50 text-green-700 border-green-200"
                                >
                                    <Trophy className="h-3 w-3" />
                                    Completed
                                </Badge>
                            )}
                        </div>
                    </div>
                </div>
            </div>

            {/* Scrollable Chat Area */}
            <div className="flex-1 overflow-hidden">
                <ScrollArea className="h-full px-4 sm:px-6 py-6" ref={scrollRef}>
                    <div className="space-y-6 max-w-4xl mx-auto pb-4">
                        {candidate.chatHistory.map((message, idx) => (
                            <div
                                key={message.id}
                                className={`flex gap-3 sm:gap-4 ${message.role === 'user' ? 'justify-end' : 'justify-start'
                                    } animate-in fade-in slide-in-from-bottom-4 duration-500`}
                                style={{ animationDelay: `${idx * 50}ms` }}
                            >
                                {message.role === 'assistant' && (
                                    <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center flex-shrink-0 shadow-lg">
                                        <Bot className="h-4 w-4 sm:h-5 sm:w-5 text-white" />
                                    </div>
                                )}

                                <div
                                    className={`rounded-2xl px-4 py-3 max-w-[85%] sm:max-w-[75%] shadow-sm ${message.role === 'user'
                                        ? 'bg-gradient-to-br from-emerald-600 to-teal-600 text-white'
                                        : 'bg-white text-slate-900 border border-slate-200'
                                        }`}
                                >
                                    <p className="text-sm leading-relaxed whitespace-pre-wrap">
                                        {message.content}
                                    </p>
                                </div>

                                {message.role === 'user' && (
                                    <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-gradient-to-br from-slate-700 to-slate-900 flex items-center justify-center flex-shrink-0 shadow-lg">
                                        <User className="h-4 w-4 sm:h-5 sm:w-5 text-white" />
                                    </div>
                                )}
                            </div>
                        ))}

                        {isProcessing && (
                            <div className="flex gap-3 sm:gap-4 justify-start animate-in fade-in slide-in-from-bottom-4">
                                <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center shadow-lg">
                                    <Bot className="h-4 w-4 sm:h-5 sm:w-5 text-white" />
                                </div>
                                <div className="rounded-2xl px-4 py-3 bg-white border border-slate-200 shadow-sm">
                                    <div className="flex items-center gap-2">
                                        <Loader2 className="h-4 w-4 animate-spin text-emerald-600" />
                                        <span className="text-sm text-slate-600">Thinking...</span>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                </ScrollArea>
            </div>

            {/* Input Bar - Sticky at bottom */}
            {candidate.status !== InterviewStatus.COMPLETED && (
                <div className="sticky bottom-0 border-t bg-white/80 backdrop-blur-xl shadow-lg z-20 flex-shrink-0">
                    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-4">
                        <div className="flex gap-2 sm:gap-3">
                            <Input
                                value={inputValue}
                                onChange={(e) => setInputValue(e.target.value)}
                                onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && handleSendMessage()}
                                placeholder={
                                    candidate.status === InterviewStatus.COLLECTING_INFO
                                        ? `Enter your ${collectingField}...`
                                        : 'Type or speak your answer...'
                                }
                                disabled={isProcessing}
                                className="flex-1 h-12 px-4 rounded-xl border-slate-200 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 transition-all"
                            />

                            {/* 🎤 Mic button - Toggle on/off */}
                            <Button
                                onClick={handleVoiceInput}
                                disabled={isProcessing}
                                type="button"
                                className={`h-12 w-12 rounded-xl flex items-center justify-center transition-all duration-300 shadow-lg ${isListening
                                    ? 'bg-red-500 hover:bg-red-600 animate-pulse'
                                    : 'bg-slate-200 hover:bg-slate-300'
                                    }`}
                                title={isListening ? 'Click to stop recording' : 'Click to start recording'}
                            >
                                {isListening ? (
                                    <MicOff className="h-5 w-5 text-white" />
                                ) : (
                                    <Mic className="h-5 w-5 text-slate-800" />
                                )}
                            </Button>

                            <Button
                                onClick={handleSendMessage}
                                disabled={!inputValue.trim() || isProcessing}
                                className="h-12 px-5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 shadow-lg transition-all"
                            >
                                <Send className="h-5 w-5 text-white" />
                            </Button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};
