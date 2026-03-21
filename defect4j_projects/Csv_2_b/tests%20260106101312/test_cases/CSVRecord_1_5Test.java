package org.apache.commons.csv;
import org.junit.jupiter.api.Timeout;
import java.io.Serializable;
import java.util.Arrays;

import static org.junit.jupiter.api.Assertions.*;

import java.lang.reflect.Constructor;
import java.lang.reflect.Method;
import java.util.Collections;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;

import org.junit.jupiter.api.Test;

class CSVRecord_1_5Test {

    @Test
    @Timeout(8000)
    void testCSVRecordConstructorAndGetters() throws Exception {
        String[] values = new String[] {"val1", "val2"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("col1", 0);
        mapping.put("col2", 1);
        String comment = "comment";
        long recordNumber = 123L;

        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        CSVRecord record = constructor.newInstance((Object) values, mapping, comment, recordNumber);

        // Test values array is set correctly
        assertEquals("val1", record.get(0));
        assertEquals("val2", record.get(1));

        // Test get(String)
        assertEquals("val1", record.get("col1"));
        assertEquals("val2", record.get("col2"));

        // Test get with invalid index throws exception
        assertThrows(IndexOutOfBoundsException.class, () -> record.get(2));

        // Test get with unmapped column throws exception
        assertThrows(IllegalArgumentException.class, () -> record.get("unknown"));

        // Test isConsistent: values length == mapping size? Yes (2 vs 2)
        assertTrue(record.isConsistent());

        // Test isMapped
        assertTrue(record.isMapped("col1"));
        assertFalse(record.isMapped("unknown"));

        // Test isSet
        assertTrue(record.isSet("col1"));
        assertFalse(record.isSet("unknown"));

        // Test iterator
        Iterator<String> iterator = record.iterator();
        assertTrue(iterator.hasNext());
        assertEquals("val1", iterator.next());
        assertEquals("val2", iterator.next());
        assertFalse(iterator.hasNext());

        // Test values() method via reflection (package-private)
        Method valuesMethod = CSVRecord.class.getDeclaredMethod("values");
        valuesMethod.setAccessible(true);
        String[] returnedValues = (String[]) valuesMethod.invoke(record);
        assertArrayEquals(values, returnedValues);

        // Test getComment
        assertEquals(comment, record.getComment());

        // Test getRecordNumber
        assertEquals(recordNumber, record.getRecordNumber());

        // Test size
        assertEquals(values.length, record.size());

        // Test toString contains values
        String toString = record.toString();
        assertTrue(toString.contains("val1"));
        assertTrue(toString.contains("val2"));
    }

    @Test
    @Timeout(8000)
    void testCSVRecordConstructorWithNullValues() throws Exception {
        Map<String, Integer> mapping = Collections.emptyMap();
        String comment = null;
        long recordNumber = 0L;

        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        CSVRecord record = constructor.newInstance((Object) null, mapping, comment, recordNumber);

        // values should be EMPTY_STRING_ARRAY internally, size 0
        assertEquals(0, record.size());
        assertFalse(record.iterator().hasNext());
        assertNull(record.getComment());
        assertEquals(0L, record.getRecordNumber());
        assertTrue(record.isConsistent());
    }
}