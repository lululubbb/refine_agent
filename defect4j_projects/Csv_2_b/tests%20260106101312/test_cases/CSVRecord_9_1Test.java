package org.apache.commons.csv;
import org.junit.jupiter.api.Timeout;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.lang.reflect.Constructor;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

import org.junit.jupiter.api.Test;

public class CSVRecord_9_1Test {

    @Test
    @Timeout(8000)
    public void testGetComment() throws Exception {
        String[] values = new String[] {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("col1", 0);
        mapping.put("col2", 1);
        String comment = "This is a comment";
        long recordNumber = 1L;

        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        CSVRecord record = constructor.newInstance((Object) values, mapping, comment, recordNumber);

        assertEquals(comment, record.getComment());
    }

    @Test
    @Timeout(8000)
    public void testGetCommentNull() throws Exception {
        String[] values = new String[] {"value1", "value2"};
        Map<String, Integer> mapping = Collections.emptyMap();
        String comment = null;
        long recordNumber = 2L;

        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        CSVRecord record = constructor.newInstance((Object) values, mapping, comment, recordNumber);

        assertEquals(comment, record.getComment());
    }
}