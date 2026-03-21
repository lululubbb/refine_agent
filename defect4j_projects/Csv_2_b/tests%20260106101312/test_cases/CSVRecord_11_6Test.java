package org.apache.commons.csv;
import org.junit.jupiter.api.Timeout;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.util.Collections;
import java.util.Map;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

public class CSVRecord_11_6Test {

    private Constructor<CSVRecord> constructor;

    @BeforeEach
    public void setUp() throws Exception {
        constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
    }

    @Test
    @Timeout(8000)
    public void testSize_withNonEmptyValues() throws Exception {
        String[] values = new String[] {"a", "b", "c"};
        Map<String, Integer> mapping = Collections.emptyMap();
        String comment = "comment";
        long recordNumber = 1L;

        CSVRecord record = constructor.newInstance((Object) values, mapping, comment, recordNumber);

        assertEquals(3, record.size());
    }

    @Test
    @Timeout(8000)
    public void testSize_withEmptyValues() throws Exception {
        String[] values = new String[0];
        Map<String, Integer> mapping = Collections.emptyMap();
        String comment = null;
        long recordNumber = 0L;

        CSVRecord record = constructor.newInstance((Object) values, mapping, comment, recordNumber);

        assertEquals(0, record.size());
    }

    @Test
    @Timeout(8000)
    public void testSize_withNullValuesField() throws Exception {
        // Create an instance with a non-null values array, then forcibly set values to null via reflection
        String[] values = new String[] {"x"};
        Map<String, Integer> mapping = Collections.emptyMap();
        String comment = null;
        long recordNumber = 0L;

        CSVRecord record = constructor.newInstance((Object) values, mapping, comment, recordNumber);

        Field valuesField = CSVRecord.class.getDeclaredField("values");
        valuesField.setAccessible(true);
        valuesField.set(record, null);

        try {
            record.size();
        } catch (NullPointerException e) {
            // Expected exception, test passes
            return;
        }
        throw new AssertionError("Expected NullPointerException when values is null");
    }
}