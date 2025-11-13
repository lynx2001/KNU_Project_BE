from django.shortcuts import render
from rest_framework import viewsets, permissions, filters
from .models import Article, Summary, SummaryGroup
from .serializers import SummarySerializer, SummaryGroupSerializer
from django.utils import timezone
from django.db.models import Max

class SummaryViewSet(viewsets.ModelViewSet):
    queryset = Summary.objects.all()
    serializer_class = SummarySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "content"]
    ordering_fields = ["title", "id"]


class SummaryGroupViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SummaryGroup.objects.prefetch_related('summaries__article').all()

    serializer_class = SummaryGroupSerializer
    permission_classes = [permissions.AllowAny]

    filter_backends = [filters.OrderingFilter]
    search_fields = ["date", "group_index"]
    ordering_fields = ["date", "group_index"]
    ordering = ["-date", "-group_index"]

def create_daily_summaries():
    today = timezone.now().date()
    last_index_data = SummaryGroup.objects.filter(date=today).aggregate(max_index=Max('group_index'))
    
    last_index = last_index_data.get('max_index')

    if last_index is None:
        next_index = 1
    else:
        next_index = last_index + 1

    new_summary_group = SummaryGroup.objects.create(date=today, group_index=next_index)
    print(f"{today} 날짜의 {next_index}번째 요약 그룹을 생성했습니다.")

    articles_to_summarize = Article.objects.all()[:3] 

    for article in articles_to_summarize:
        summary_content = ""
        if article.content:
            summary_content = f"{article.content[:100]}..."
        Summary.objects.create(
            article=article,
            group=new_summary_group,
            title=article.title,
            content=summary_content
        )
    
    print("3개의 요약문을 성공적으로 저장했습니다.")