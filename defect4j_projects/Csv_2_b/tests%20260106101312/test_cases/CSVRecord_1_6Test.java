package org.apache.commons.csv;
import org.junit.jupiter.api.Timeout;
import java.io.Serializable;
import java.util.Arrays;

import static org.junit.jupiter.api.Assertions.*;

import java.lang.reflect.Constructor;
import java.util.Collections;
import java.util.Iterator;
import java.util.Map;

import org.junit.jupiter.api.Test;

public class CSVRecord_1_6Test {

    @Test
    @Timeout(8000)
    void testCSVRecordConstructorAndGetters() throws Exception {
        String[] values = new String[] { "a", "b", "c" };
        Map<String, Integer> mapping = Map.of("col1", 0, "col2", 1, "col3", 2);
        String comment = "comment";
        long recordNumber = 42L;

        // Use reflection to invoke the constructor since it is package-private
        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        CSVRecord record = constructor.newInstance((Object) values, mapping, comment, recordNumber);

        // Validate fields via public methods
        assertEquals("a", record.get(0));
        assertEquals("b", record.get(1));
        assertEquals("c", record.get(2));
        assertEquals("a", record.get("col1"));
        assertEquals("b", record.get("col2"));
        assertEquals("c", record.get("col3"));
        assertEquals(comment, record.getComment());
        assertEquals(recordNumber, record.getRecordNumber());
        assertEquals(3, record.size());

        assertTrue(record.isConsistent());
        assertTrue(record.isMapped("col1"));
        assertFalse(record.isMapped("colX"));
        assertTrue(record.isSet("col1"));
        assertFalse(record.isSet("colX"));

        Iterator<String> iterator = record.iterator();
        assertNotNull(iterator);
        assertTrue(iterator.hasNext());
        assertEquals("a", iterator.next());

        String[] vals = record.values();
        assertArrayEquals(values, vals);

        String toStringResult = record.toString();
        assertNotNull(toStringResult);
        assertTrue(toStringResult.contains("a"));
        assertTrue(toStringResult.contains("b"));
        assertTrue(toStringResult.contains("c"));
        assertTrue(toStringResult.contains("comment"));

        // Test constructor with null values array -> should use EMPTY_STRING_ARRAY
        CSVRecord record2 = constructor.newInstance((Object) null, Collections.emptyMap(), null, 0L);
        assertEquals(0, record2.size());
        assertFalse(record2.iterator().hasNext());
        assertNull(record2.getComment());
    }
}