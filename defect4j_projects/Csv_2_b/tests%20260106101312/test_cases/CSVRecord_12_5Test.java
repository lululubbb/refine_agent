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

public class CSVRecord_12_5Test {

    @Test
    @Timeout(8000)
    public void testToString_withValues() throws Exception {
        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        String[] values = new String[] { "a", "b", "c" };
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = constructor.newInstance((Object) values, mapping, null, 1L);
        String expected = "[a, b, c]";
        assertEquals(expected, record.toString());
    }

    @Test
    @Timeout(8000)
    public void testToString_withEmptyValues() throws Exception {
        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        String[] values = new String[0];
        Map<String, Integer> mapping = Collections.emptyMap();
        CSVRecord record = constructor.newInstance((Object) values, mapping, null, 1L);
        String expected = "[]";
        assertEquals(expected, record.toString());
    }

    @Test
    @Timeout(8000)
    public void testToString_withNullValues() throws Exception {
        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        // Pass null for values; toString returns "null" because values is null
        CSVRecord record = constructor.newInstance((Object) null, null, null, 1L);
        String expected = "null";
        assertEquals(expected, record.toString());
    }
}