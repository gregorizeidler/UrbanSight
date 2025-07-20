"""
Conversational AI Agent
IA Conversacional para interação em tempo real sobre análises urbanas
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from openai import OpenAI
import json
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class ChatMessage:
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime
    context_type: Optional[str] = None  # "analysis", "recommendation", "comparison"

@dataclass
class ConversationContext:
    analysis_result: Any
    user_profile: Optional[Dict[str, Any]] = None
    conversation_history: List[ChatMessage] = None
    current_topic: Optional[str] = None
    
    def __post_init__(self):
        if self.conversation_history is None:
            self.conversation_history = []

@dataclass
class ConversationalResponse:
    message: str
    suggested_questions: List[str]
    relevant_data: Dict[str, Any]
    visualization_suggestions: List[str]
    follow_up_actions: List[str]

class ConversationalAI:
    """IA Conversacional especializada em análises urbanas"""
    
    def __init__(self, openai_api_key: Optional[str] = None):
        self.openai_client = OpenAI(api_key=openai_api_key) if openai_api_key else None
        self.context_memory = {}
        
    async def chat(self, 
                   user_message: str,
                   session_id: str,
                   context: ConversationContext) -> ConversationalResponse:
        """Processa mensagem do usuário e gera resposta conversacional"""
        
        try:
            # Adicionar mensagem do usuário ao histórico
            user_msg = ChatMessage(
                role="user",
                content=user_message,
                timestamp=datetime.now()
            )
            context.conversation_history.append(user_msg)
            
            # Analisar intenção do usuário
            intent = await self._analyze_user_intent(user_message, context)
            
            # Gerar resposta baseada na intenção
            response = await self._generate_contextual_response(user_message, intent, context)
            
            # Adicionar resposta ao histórico
            assistant_msg = ChatMessage(
                role="assistant",
                content=response.message,
                timestamp=datetime.now(),
                context_type=intent
            )
            context.conversation_history.append(assistant_msg)
            
            # Armazenar contexto na memória
            self.context_memory[session_id] = context
            
            return response
            
        except Exception as e:
            logger.error(f"Erro no chat conversacional: {str(e)}")
            return ConversationalResponse(
                message="Desculpe, ocorreu um erro. Pode repetir sua pergunta?",
                suggested_questions=[
                    "Como está a segurança da região?",
                    "Qual o potencial de investimento?",
                    "É uma boa área para famílias?"
                ],
                relevant_data={},
                visualization_suggestions=[],
                follow_up_actions=[]
            )
    
    async def _analyze_user_intent(self, message: str, context: ConversationContext) -> str:
        """Analisa a intenção por trás da mensagem do usuário"""
        
        # Intenções simples baseadas em palavras-chave
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['preço', 'valor', 'investimento', 'roi', 'retorno']):
            return "investment_inquiry"
        elif any(word in message_lower for word in ['família', 'criança', 'escola', 'playground']):
            return "family_inquiry" 
        elif any(word in message_lower for word in ['segurança', 'crime', 'roubo', 'violência']):
            return "safety_inquiry"
        elif any(word in message_lower for word in ['transporte', 'ônibus', 'metrô', 'mobilidade']):
            return "transport_inquiry"
        elif any(word in message_lower for word in ['compare', 'comparar', 'melhor', 'diferença']):
            return "comparison_request"
        elif any(word in message_lower for word in ['futuro', 'desenvolvimento', 'crescimento', 'tendência']):
            return "future_inquiry"
        elif any(word in message_lower for word in ['negócio', 'comercial', 'loja', 'empresa']):
            return "business_inquiry"
        elif any(word in message_lower for word in ['resumo', 'geral', 'overview', 'principais']):
            return "summary_request"
        else:
            return "general_inquiry"
    
    async def _generate_contextual_response(self, 
                                          user_message: str,
                                          intent: str,
                                          context: ConversationContext) -> ConversationalResponse:
        """Gera resposta contextual baseada na intenção"""
        
        # Extrair dados relevantes baseados na intenção
        relevant_data = self._extract_relevant_data(intent, context.analysis_result)
        
        # Gerar resposta com IA
        ai_response = await self._generate_ai_response(user_message, intent, relevant_data, context)
        
        # Gerar sugestões de perguntas
        suggested_questions = self._generate_suggested_questions(intent, context.analysis_result)
        
        # Gerar sugestões de visualização
        viz_suggestions = self._generate_visualization_suggestions(intent)
        
        # Gerar ações de follow-up
        follow_up_actions = self._generate_follow_up_actions(intent, context.analysis_result)
        
        return ConversationalResponse(
            message=ai_response,
            suggested_questions=suggested_questions,
            relevant_data=relevant_data,
            visualization_suggestions=viz_suggestions,
            follow_up_actions=follow_up_actions
        )
    
    def _extract_relevant_data(self, intent: str, analysis_result: Any) -> Dict[str, Any]:
        """Extrai dados relevantes baseados na intenção"""
        
        data = {}
        
        if intent == "investment_inquiry":
            if hasattr(analysis_result, 'investment_analysis') and analysis_result.investment_analysis:
                inv = analysis_result.investment_analysis
                data = {
                    'investment_score': getattr(inv, 'investment_score', 0),
                    'roi_potential': getattr(inv, 'roi_potential', 0),
                    'risk_level': getattr(inv, 'risk_level', 0)
                }
        
        elif intent == "family_inquiry":
            if hasattr(analysis_result, 'family_habitability') and analysis_result.family_habitability:
                fam = analysis_result.family_habitability
                data = {
                    'overall_family_score': getattr(fam, 'overall_family_score', 0),
                    'children_metrics': getattr(fam, 'children_metrics', None),
                    'family_analyses': getattr(fam, 'family_analyses', [])
                }
        
        elif intent == "safety_inquiry":
            if hasattr(analysis_result, 'metrics') and analysis_result.metrics:
                data = {
                    'safety_score': getattr(analysis_result.metrics, 'safety_score', 0)
                }
        
        elif intent == "transport_inquiry":
            if hasattr(analysis_result, 'metrics') and analysis_result.metrics:
                data = {
                    'accessibility_score': getattr(analysis_result.metrics, 'accessibility_score', 0)
                }
        
        elif intent == "future_inquiry":
            if hasattr(analysis_result, 'predictive_analysis') and analysis_result.predictive_analysis:
                pred = analysis_result.predictive_analysis
                data = {
                    'confidence_rating': getattr(pred, 'confidence_rating', 0),
                    'market_forecasting': getattr(pred, 'market_forecasting', None)
                }
        
        elif intent == "business_inquiry":
            if hasattr(analysis_result, 'commercial_viability') and analysis_result.commercial_viability:
                comm = analysis_result.commercial_viability
                data = {
                    'overall_commercial_score': getattr(comm, 'overall_commercial_score', 0),
                    'business_opportunities': getattr(comm, 'business_opportunities', [])
                }
        
        return data
    
    async def _generate_ai_response(self, 
                                  user_message: str,
                                  intent: str,
                                  relevant_data: Dict[str, Any],
                                  context: ConversationContext) -> str:
        """Gera resposta usando IA"""
        
        if not self.openai_client:
            return self._generate_fallback_response(intent, relevant_data)
        
        try:
            # Preparar contexto da conversa
            conversation_context = "\n".join([
                f"{msg.role}: {msg.content}" 
                for msg in context.conversation_history[-5:]  # Últimas 5 mensagens
            ])
            
            # Preparar dados relevantes
            data_context = json.dumps(relevant_data, ensure_ascii=False, indent=2)
            
            prompt = f"""
            Você é um assistente especializado em análise urbana e imobiliária. Responda de forma conversacional e útil.
            
            CONTEXTO DA CONVERSA:
            {conversation_context}
            
            PERGUNTA ATUAL: {user_message}
            INTENÇÃO DETECTADA: {intent}
            
            DADOS RELEVANTES:
            {data_context}
            
            Instruções:
            1. Seja conversacional e amigável
            2. Use os dados específicos na resposta
            3. Seja conciso mas informativo
            4. Se necessário, explique os números de forma compreensível
            5. Mantenha foco na pergunta específica
            
            Responda em português brasileiro de forma natural e útil.
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Você é um assistente especializado em análise urbana, sempre prestativo e informativo."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Erro gerando resposta de IA: {str(e)}")
            return self._generate_fallback_response(intent, relevant_data)
    
    def _generate_fallback_response(self, intent: str, relevant_data: Dict[str, Any]) -> str:
        """Gera resposta de fallback quando IA não está disponível"""
        
        if intent == "investment_inquiry":
            score = relevant_data.get('investment_score', 0)
            return f"Com base na análise, o score de investimento da região é {score:.1f}/100. Esta métrica considera fatores como potencial de valorização e riscos."
        
        elif intent == "family_inquiry":
            score = relevant_data.get('overall_family_score', 0)
            return f"Para famílias, a região tem um score de adequação de {score:.1f}/100, considerando aspectos como escolas, segurança e áreas de lazer."
        
        elif intent == "safety_inquiry":
            score = relevant_data.get('safety_score', 0)
            return f"O score de segurança da região é {score:.1f}/100, baseado em fatores como iluminação, presença de comércios e fluxo de pessoas."
        
        else:
            return "Posso ajudar com informações sobre investimento, segurança, adequação familiar e outros aspectos da região. O que você gostaria de saber?"
    
    def _generate_suggested_questions(self, intent: str, analysis_result: Any) -> List[str]:
        """Gera perguntas sugeridas baseadas na intenção"""
        
        suggestions = {
            "investment_inquiry": [
                "Qual o potencial de valorização a longo prazo?",
                "Quais são os principais riscos de investimento?",
                "Como está o mercado imobiliário da região?"
            ],
            "family_inquiry": [
                "Quantas escolas tem na região?",
                "É seguro para crianças brincarem?",
                "Tem atividades para jovens?"
            ],
            "safety_inquiry": [
                "Como é a segurança durante a noite?",
                "Tem policiamento na região?",
                "Quais as áreas mais seguras próximas?"
            ],
            "business_inquiry": [
                "Que tipo de negócio funcionaria bem aqui?",
                "Como está a concorrência local?",
                "Qual o fluxo de pessoas na região?"
            ],
            "future_inquiry": [
                "Que projetos estão planejados para a região?",
                "Como será o desenvolvimento nos próximos anos?",
                "Vale a pena investir pensando no futuro?"
            ]
        }
        
        return suggestions.get(intent, [
            "Me conte mais sobre a região",
            "Quais são os pontos fortes?",
            "O que precisa melhorar?"
        ])
    
    def _generate_visualization_suggestions(self, intent: str) -> List[str]:
        """Gera sugestões de visualização baseadas na intenção"""
        
        viz_suggestions = {
            "investment_inquiry": [
                "Gráfico de projeção de valorização",
                "Comparação com outras regiões",
                "Dashboard de métricas de investimento"
            ],
            "family_inquiry": [
                "Mapa de escolas e playgrounds",
                "Score por tipo de família",
                "Análise de segurança infantil"
            ],
            "safety_inquiry": [
                "Mapa de segurança da região",
                "Gráfico de scores de segurança",
                "Comparação temporal"
            ],
            "business_inquiry": [
                "Análise de concorrência",
                "Mapa de oportunidades",
                "Fluxo de pessoas por horário"
            ]
        }
        
        return viz_suggestions.get(intent, [
            "Visão geral da região",
            "Principais indicadores",
            "Mapa interativo"
        ])
    
    def _generate_follow_up_actions(self, intent: str, analysis_result: Any) -> List[str]:
        """Gera ações de follow-up baseadas na intenção"""
        
        actions = {
            "investment_inquiry": [
                "Ver análise detalhada de investimento",
                "Comparar com outras opções",
                "Agendar visita à região"
            ],
            "family_inquiry": [
                "Explorar escolas da região",
                "Ver relatório de habitabilidade",
                "Buscar atividades para crianças"
            ],
            "business_inquiry": [
                "Ver oportunidades de negócio",
                "Analisar viabilidade comercial",
                "Estudar concorrência local"
            ]
        }
        
        return actions.get(intent, [
            "Explorar mais análises",
            "Ver recomendações personalizadas",
            "Acessar dashboard completo"
        ]) 