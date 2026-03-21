package org.apache.commons.csv;
import org.junit.jupiter.api.Timeout;
import java.io.Serializable;
import java.util.Arrays;

import static org.junit.jupiter.api.Assertions.*;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Constructor;
import java.util.Collections;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;

public class CSVRecord_1_3Test {

    @Test
    @Timeout(8000)
    public void testConstructorAndGetters() throws Exception {
        String[] values = new String[] {"a", "b", "c"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("col1", 0);
        mapping.put("col2", 1);
        String comment = "comment";
        long recordNumber = 123L;

        // Using reflection to invoke package-private constructor
        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        CSVRecord record = constructor.newInstance((Object) values, mapping, comment, recordNumber);

        // Validate fields via public methods
        assertEquals("a", record.get(0));
        assertEquals("b", record.get(1));
        assertEquals("c", record.get(2));
        assertEquals("a", record.get("col1"));
        assertEquals("b", record.get("col2"));
        assertEquals(comment, record.getComment());
        assertEquals(recordNumber, record.getRecordNumber());
        assertEquals(3, record.size());
        assertTrue(record.isMapped("col1"));
        assertFalse(record.isMapped("colX"));
        assertTrue(record.isSet("col1"));
        assertFalse(record.isSet("colX"));
        assertTrue(record.isConsistent());

        // Iterator test
        Iterator<String> it = record.iterator();
        assertTrue(it.hasNext());
        assertEquals("a", it.next());
        assertEquals("b", it.next());
        assertEquals("c", it.next());
        assertFalse(it.hasNext());

        // toString contains values
        String toString = record.toString();
        assertTrue(toString.contains("a"));
        assertTrue(toString.contains("b"));
        assertTrue(toString.contains("c"));
    }

    @Test
    @Timeout(8000)
    public void testConstructorWithNullValues() throws Exception {
        Map<String, Integer> mapping = Collections.emptyMap();
        String comment = null;
        long recordNumber = 0L;

        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        // Pass null as Object to avoid varargs ambiguity
        CSVRecord record = constructor.newInstance((Object) null, mapping, comment, recordNumber);

        // values should be empty array, size 0
        assertEquals(0, record.size());
        assertFalse(record.iterator().hasNext());
        assertEquals(comment, record.getComment());
        assertEquals(recordNumber, record.getRecordNumber());
    }

    @Test
    @Timeout(8000)
    public void testGetWithInvalidIndex() throws Exception {
        String[] values = new String[] {"x"};
        Map<String, Integer> mapping = Collections.emptyMap();

        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        CSVRecord record = constructor.newInstance((Object) values, mapping, null, 1L);

        assertThrows(ArrayIndexOutOfBoundsException.class, () -> record.get(1));
    }

    @Test
    @Timeout(8000)
    public void testGetWithInvalidName() throws Exception {
        String[] values = new String[] {"x"};
        Map<String, Integer> mapping = Collections.emptyMap();

        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        CSVRecord record = constructor.newInstance((Object) values, mapping, null, 1L);

        assertThrows(IllegalArgumentException.class, () -> record.get("invalid"));
    }

    @Test
    @Timeout(8000)
    public void testIsConsistentFalse() throws Exception {
        String[] values = new String[] {"a", "b"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("col1", 0);
        mapping.put("col2", 1);
        mapping.put("col3", 2);

        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        CSVRecord record = constructor.newInstance((Object) values, mapping, null, 1L);

        // values length 2, mapping size 3 => inconsistent
        assertFalse(record.isConsistent());
    }
}